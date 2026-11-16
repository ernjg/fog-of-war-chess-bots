// ---------------------------------------------------------------------------------------
// Stockfish processes driven from the helper, so that the tree's leaves are valued without
// a round trip through Python per node. Same protocol and value scale as eBotI/engine.py:
// Threads 1, MultiPV 256, depth-limited searches, values tanh(cp / 600) with a small tail.
// Engines live in the bot's process group, so the arena pauses them with everything else.

#include <sys/wait.h>
#include <poll.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>

namespace engines {

static const double CP_SCALE = 600.0, MAX_CP_VALUE = 0.99, CP_TAIL = 0.01, CP_LIMIT = 20000.0;

static double cp_value(double cp) {
    double tail = std::max(-1.0, std::min(1.0, cp / CP_LIMIT));
    return (MAX_CP_VALUE - CP_TAIL) * std::tanh(cp / CP_SCALE) + CP_TAIL * tail;
}
static double mate_value(int moves) {
    double size = 1.0 - 0.0001 * std::min(std::abs(moves), 50);
    return moves > 0 ? size : -size;
}

struct Engine {
    pid_t pid = -1;
    int to = -1, from = -1;     // our write end, our read end
    std::string buffer;
    bool dead = true;
};

struct Result {
    bool ok = false;
    int depth = 0;
    std::unordered_map<std::string, double> scores;   // UCI -> value for the side to move
};

static std::vector<Engine> E;
static std::string BINARY;
static int HASH = 64;

static void kill_engine(Engine& e) {
    if (e.pid > 0) { ::kill(e.pid, SIGKILL); waitpid(e.pid, nullptr, 0); }
    if (e.to >= 0) close(e.to);
    if (e.from >= 0) close(e.from);
    e.pid = -1; e.to = e.from = -1; e.dead = true; e.buffer.clear();
}

static void shutdown() { for (Engine& e : E) kill_engine(e); E.clear(); }

static bool send(Engine& e, const std::string& text) {
    if (e.dead) return false;
    size_t done = 0;
    while (done < text.size()) {
        ssize_t n = write(e.to, text.data() + done, text.size() - done);
        if (n < 0) { if (errno == EINTR) continue; kill_engine(e); return false; }
        done += (size_t)n;
    }
    return true;
}

// One line from the engine within `ms`, or false (timeout, EOF, or dead).
static bool read_line(Engine& e, std::string& line, double ms) {
    Clock::time_point start = Clock::now();
    for (;;) {
        size_t at = e.buffer.find('\n');
        if (at != std::string::npos) { line = e.buffer.substr(0, at); e.buffer.erase(0, at + 1); return true; }
        if (e.buffer.size() > (1u << 20)) { kill_engine(e); return false; }
        double left = ms - ms_since(start);
        if (left <= 0) return false;
        pollfd pfd{e.from, POLLIN, 0};
        int r = poll(&pfd, 1, (int)std::max(1.0, left));
        if (r < 0) { if (errno == EINTR) continue; kill_engine(e); return false; }
        if (r == 0) return false;
        char chunk[16384];
        ssize_t n = read(e.from, chunk, sizeof chunk);
        if (n <= 0) { if (n < 0 && errno == EINTR) continue; kill_engine(e); return false; }
        e.buffer.append(chunk, (size_t)n);
    }
}

static bool wait_for(Engine& e, const char* word, double ms) {
    Clock::time_point start = Clock::now();
    std::string line;
    while (read_line(e, line, ms - ms_since(start)))
        if (line.rfind(word, 0) == 0) return true;
    return false;
}

static bool spawn(Engine& e, double ms) {
    int to_engine[2], from_engine[2];
    if (pipe(to_engine) || pipe(from_engine)) return false;
    pid_t pid = fork();
    if (pid < 0) return false;
    if (pid == 0) {
        dup2(to_engine[0], 0); dup2(from_engine[1], 1);
        close(to_engine[0]); close(to_engine[1]); close(from_engine[0]); close(from_engine[1]);
        std::string dir = BINARY.substr(0, BINARY.rfind('/'));
        if (!dir.empty() && chdir(dir.c_str())) {}
        execl(BINARY.c_str(), BINARY.c_str(), (char*)nullptr);
        _exit(127);
    }
    close(to_engine[0]); close(from_engine[1]);
    e.pid = pid; e.to = to_engine[1]; e.from = from_engine[0]; e.dead = false; e.buffer.clear();
    fcntl(e.from, F_SETFL, fcntl(e.from, F_GETFL) | O_NONBLOCK);
    Clock::time_point start = Clock::now();
    if (!send(e, "uci\n") || !wait_for(e, "uciok", ms)) { kill_engine(e); return false; }
    std::string options = "setoption name Threads value 1\nsetoption name Hash value " + std::to_string(HASH) +
                          "\nsetoption name MultiPV value 256\nisready\n";
    if (!send(e, options) || !wait_for(e, "readyok", ms - ms_since(start))) { kill_engine(e); return false; }
    if (!send(e, "position startpos\ngo depth 1\n") || !wait_for(e, "bestmove", ms - ms_since(start))) { kill_engine(e); return false; }
    return true;
}

static int start(const std::string& binary, int count, int hash, double ms) {
    shutdown();
    BINARY = binary; HASH = hash;
    E.assign((size_t)std::max(count, 0), Engine());
    int ready = 0;
    for (Engine& e : E) if (spawn(e, ms)) ++ready;
    return ready;
}

static int ready_count() { int n = 0; for (const Engine& e : E) if (!e.dead) ++n; return n; }

// "info depth D ... multipv K score cp X ... pv M ..." -> (depth, move, value); false for the rest.
static bool parse_info(const std::string& line, int& depth, std::string& move, double& value) {
    if (line.rfind("info ", 0) != 0) return false;
    std::istringstream in(line);
    std::string word, kind;
    depth = -1; int amount = 0; bool bound = false, have_score = false, have_pv = false;
    while (in >> word) {
        if (word == "depth") in >> depth;
        else if (word == "currmove") return false;
        else if (word == "score") { in >> kind >> amount; have_score = true; }
        else if (word == "lowerbound" || word == "upperbound") bound = true;
        else if (word == "pv") { in >> move; have_pv = !move.empty(); break; }
    }
    if (depth < 0 || !have_score || !have_pv || bound) return false;
    value = kind == "mate" ? mate_value(amount) : cp_value((double)amount);
    return true;
}

// Score every position with MultiPV at `depth`, sharing the live engines, until `deadline`.
static void evaluate(const std::vector<std::string>& fens, int depth, Clock::time_point deadline,
                     std::vector<Result>& results) {
    results.assign(fens.size(), Result());
    size_t next = 0;
    std::vector<long> job(E.size(), -1);
    std::vector<std::unordered_map<std::string, double>> current(E.size()), previous(E.size());
    std::vector<int> cur_depth(E.size(), -1);
    auto assign = [&](size_t i) {
        Engine& e = E[i];
        if (e.dead || next >= fens.size()) { job[i] = -1; return; }
        job[i] = (long)next;
        current[i].clear(); previous[i].clear(); cur_depth[i] = -1;
        if (!send(e, "position fen " + fens[next] + "\ngo depth " + std::to_string(depth) + "\n")) job[i] = -1;
        ++next;
    };
    for (size_t i = 0; i < E.size(); ++i) assign(i);
    bool stopped = false;
    Clock::time_point stop_sent;
    for (;;) {
        bool any = false;
        std::vector<pollfd> fds;
        std::vector<size_t> who;
        for (size_t i = 0; i < E.size(); ++i) if (job[i] >= 0 && !E[i].dead) { fds.push_back({E[i].from, POLLIN, 0}); who.push_back(i); any = true; }
        if (!any) break;
        double left = std::chrono::duration<double, std::milli>(deadline - Clock::now()).count();
        if (left <= 0 && !stopped) { for (size_t i : who) send(E[i], "stop\n"); stopped = true; stop_sent = Clock::now(); }
        if (stopped) left = 500.0 - ms_since(stop_sent);   // the grace after "stop", as engine.py gives
        if (left <= 0) { for (size_t i : who) { kill_engine(E[i]); job[i] = -1; } break; }
        int r = poll(fds.data(), (nfds_t)fds.size(), (int)std::max(1.0, std::min(left, 50.0)));
        if (r < 0 && errno != EINTR) break;
        for (size_t k = 0; k < fds.size(); ++k) {
            if (!(fds[k].revents & (POLLIN | POLLHUP | POLLERR))) continue;
            size_t i = who[k];
            Engine& e = E[i];
            char chunk[16384];
            ssize_t n = read(e.from, chunk, sizeof chunk);
            if (n <= 0) { if (n < 0 && (errno == EAGAIN || errno == EINTR)) continue; kill_engine(e); job[i] = -1; continue; }
            e.buffer.append(chunk, (size_t)n);
            size_t at;
            while ((at = e.buffer.find('\n')) != std::string::npos) {
                std::string line = e.buffer.substr(0, at);
                e.buffer.erase(0, at + 1);
                int d; std::string move; double value;
                if (line.rfind("bestmove", 0) == 0) {
                    Result& res = results[(size_t)job[i]];
                    res.scores = previous[i];
                    for (auto& kv : current[i]) res.scores[kv.first] = kv.second;
                    res.ok = !res.scores.empty();
                    res.depth = cur_depth[i];
                    if (stopped) job[i] = -1; else assign(i);
                } else if (parse_info(line, d, move, value)) {
                    if (d != cur_depth[i]) { if (d > cur_depth[i]) { for (auto& kv : current[i]) previous[i][kv.first] = kv.second; current[i].clear(); cur_depth[i] = d; } else continue; }
                    current[i][move] = value;
                }
            }
        }
    }
}

}  // namespace engines
