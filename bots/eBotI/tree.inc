// ---------------------------------------------------------------------------------------
// The game tree of Obscuro's search (Zhang and Sandholm, arXiv:2506.01242, sections 3 and
// C), kept here so that it grows and solves at C++ speed. It mirrors eBotI/gametree.py:
// one-sided GT-CFR expansion with a PUCT exploring mix, PCFR+ (last iterate), the Resolve
// and Maxmargin gadgets above the roots, carry-over between turns with alternate values
// and gifts, KLUSS roots. Python drives it over the command protocol (see "tree" in
// main): it decides the time, asks Stockfish for the leaf values, and picks the move.
// Values are from our side, in [-1, 1]. Included by positions.cpp after the Set code.

#include <unordered_map>
#include <unordered_set>
#include <cmath>

namespace tree {

enum { OURS = 0, THEIRS = 1 };
enum { EXPANDED = 1, TERMINAL = 2 };
static const double NEVER_EXIT = -2.0;   // an alternate value below every payoff: always enter
static const double PUCT_C = 1.0;

struct Node {
    Pos pos;
    int32_t parent = -1;
    int32_t first_child = -1;
    int32_t infoset = -1;
    int32_t slot = -1;            // slot (in the parent's actor's space) that leads here
    int32_t prev_iset[2] = {-1, -1};
    int32_t prev_slot[2] = {-1, -1};
    int32_t root_J = -1;          // the opponent's root infoset of this node's root
    float root_p = 0;             // p(h | J), unnormalized, roots only
    float leaf = 0;               // value while unexpanded, or the decided value
    uint16_t n_children = 0;
    uint8_t actor = OURS;
    uint8_t flags = 0;
    uint8_t depth = 0;
    Move move = 0;
};

struct Infoset {
    uint8_t player;
    int32_t start;                // first slot in the player's slot space
    uint16_t n;                   // actions
    std::vector<int32_t> nodes;
    uint32_t visits = 0;          // N(I), expansion walks through it
};

struct Side {                     // one player's slot space
    std::vector<double> regret, strategy, visits, u_count, u_sum, u_sq, cfv, u;
    std::vector<int32_t> slot_infoset;
    std::vector<Move> slot_move;
    size_t size() const { return regret.size(); }
    void add(int32_t infoset, const Move* moves, int n, const double* initial) {
        for (int k = 0; k < n; ++k) {
            regret.push_back(0); strategy.push_back(initial[k]); visits.push_back(0);
            u_count.push_back(2); u_sum.push_back(0); u_sq.push_back(2); cfv.push_back(0); u.push_back(0);
            slot_infoset.push_back(infoset); slot_move.push_back(moves[k]);
        }
    }
};

struct Tree {
    int side = WHITE;
    std::vector<Node> nodes;
    std::vector<Infoset> isets;
    std::unordered_map<std::string, int32_t> iset_key;
    Side sides[2];
    // the root view
    std::string root_obs;
    std::vector<Move> root_moves;
    int32_t root_infoset = -1;
    // the gadget
    std::vector<double> alt, y_blueprint, J_weight, alpha;
    std::vector<double> res_regret, res_strategy;   // 2 per J: enter, exit
    std::vector<double> mm_regret, mm_strategy;     // 1 per J
    std::vector<uint8_t> fresh_J;                   // 1 for a J made this turn (alt still to set)
    double pmax = 1.0;
    bool gadget_ready = false;
    bool has_pass = false;
    double v_star = NEVER_EXIT;
    bool have_v_star = false;
    // the last pass
    std::vector<double> reach_x, reach_y, f_ours, f_theirs, val, V, piJ, fJ;
    std::vector<std::vector<int32_t>> roots_of_J;
    long iterations = 0;
    bool track_stability = false;
    std::vector<uint8_t> stable;
    unsigned fullmove = 1;
    std::unordered_set<U64> root_hashes;
    Rng rng;
};

static Tree* T = nullptr;   // the current tree
static Tree* OLD = nullptr; // the previous turn's, until the new one is started

static inline int actor_of(const Tree& t, const Pos& p) { return p.turn == t.side ? OURS : THEIRS; }

// The material-plus-mobility heuristic of evaluation.py, for leaves Stockfish did not value.
static double heuristic(const Tree& t, const Pos& p) {
    static const double value[6] = {1, 3, 3, 5, 9, 0};
    double advantage = 0;
    for (int piece = 0; piece < 5; ++piece)
        advantage += value[piece] * ((double)__builtin_popcountll(p.bb[piece] & p.occ[t.side]) - (double)__builtin_popcountll(p.bb[piece] & p.occ[t.side ^ 1]));
    U64 all = p.occ[0] | p.occ[1];
    double seen[2];
    for (int c = 0; c < 2; ++c) {
        U64 own = p.occ[c], s = own;
        for (U64 b = p.bb[KNIGHT] & own; b; b &= b - 1) s |= KNIGHT_ATT[lsb(b)];
        for (U64 b = p.bb[KING] & own; b; b &= b - 1) s |= KING_ATT[lsb(b)];
        for (U64 b = (p.bb[BISHOP] | p.bb[QUEEN]) & own; b; b &= b - 1) s |= bishop_att(lsb(b), all);
        for (U64 b = (p.bb[ROOK] | p.bb[QUEEN]) & own; b; b &= b - 1) s |= rook_att(lsb(b), all);
        for (U64 b = p.bb[PAWN] & own; b; b &= b - 1) s |= PAWN_ATT[c][lsb(b)];
        seen[c] = (double)__builtin_popcountll(s);
    }
    advantage += 0.05 * (seen[t.side] - seen[t.side ^ 1]);
    return std::tanh(advantage / 5.0);
}

static void sort_moves(Move* moves, int n) {  // by UCI text, as the Python tree orders them
    std::sort(moves, moves + n, [](Move a, Move b) { return to_uci(a) < to_uci(b); });
}

static std::string key_of(const Tree& t, const Node& n, int actor, const Move* moves, int count) {
    std::string key;
    key.reserve(128);
    key += (char)('0' + actor);
    if (actor == THEIRS && n.prev_iset[THEIRS] < 0) key += "J" + std::to_string(n.root_J);
    else key += std::to_string(n.prev_iset[actor]) + ":" + std::to_string(n.prev_slot[actor]);
    key += "|";
    key += observation(n.pos, actor == OURS ? t.side : t.side ^ 1);
    key += "|";
    for (int k = 0; k < count; ++k) { key += to_uci(moves[k]); key += ' '; }
    return key;
}

static int32_t add_node(Tree& t, const Pos& p, int32_t parent, Move move, int depth, int32_t J, float root_p, int32_t slot) {
    Node n;
    n.pos = p; n.parent = parent; n.move = move; n.depth = (uint8_t)std::min(depth, 255);
    n.actor = (uint8_t)actor_of(t, p); n.root_J = J; n.root_p = root_p; n.slot = slot;
    t.nodes.push_back(n);
    return (int32_t)t.nodes.size() - 1;
}

static int32_t new_J(Tree& t, double alt, double y, double weight, bool fresh) {
    t.alt.push_back(alt); t.y_blueprint.push_back(y); t.J_weight.push_back(weight); t.fresh_J.push_back(fresh ? 1 : 0);
    t.gadget_ready = false;
    return (int32_t)t.alt.size() - 1;
}

static int32_t add_root(Tree& t, const Pos& p, int32_t J, float root_p) {
    int32_t node = add_node(t, p, -1, 0, 0, J, root_p, -1);
    t.root_hashes.insert(hash_state(p));
    return node;
}

static void set_root_view(Tree& t, const std::string& obs, const std::vector<Move>& moves) {
    t.root_obs = obs; t.root_moves = moves;
    Node probe; probe.prev_iset[OURS] = -1; probe.prev_slot[OURS] = -1;
    // the key of our root infoset is computed from a root node when one is expanded
    t.root_infoset = -1;
}

static bool is_root_view_node(const Tree& t, const Node& n) {
    return n.depth == 0 && n.actor == OURS && observation(n.pos, t.side) == t.root_obs;
}

static int32_t infoset_for(Tree& t, int32_t node, const Move* moves, int count) {
    Node& n = t.nodes[node];
    int actor = n.actor;
    std::string key = key_of(t, n, actor, moves, count);
    auto found = t.iset_key.find(key);
    if (found != t.iset_key.end()) return found->second;
    Infoset is;
    is.player = (uint8_t)actor; is.start = (int32_t)t.sides[actor].size(); is.n = (uint16_t)count;
    t.isets.push_back(is);
    int32_t id = (int32_t)t.isets.size() - 1;
    t.iset_key[key] = id;
    if (actor == OURS && n.depth == 0 && n.prev_iset[OURS] < 0 && is_root_view_node(t, n)) t.root_infoset = id;
    return id;
}

// Expand `node`: `values` are Stockfish's for the side to move there (UCI -> value), or empty.
static int expand(Tree& t, int32_t node, const std::unordered_map<std::string, double>& values) {
    Node& n0 = t.nodes[node];
    if (n0.flags & (EXPANDED | TERMINAL)) return 0;
    Move moves[MAX_MOVES];
    int count = gen_moves(n0.pos, moves);
    if (n0.depth == 0 && n0.actor == OURS && is_root_view_node(t, n0)) {
        Move legal[MAX_MOVES];
        std::copy(moves, moves + count, legal);
        int kept = 0;
        for (Move m : t.root_moves) if (std::find(legal, legal + count, m) != legal + count) moves[kept++] = m;
        count = kept;
    } else sort_moves(moves, count);
    if (!count) { n0.flags |= TERMINAL; n0.leaf = n0.actor == OURS ? -1.0f : 1.0f; return 0; }
    int actor = n0.actor;
    double sign = actor == OURS ? 1.0 : -1.0;
    int32_t infoset = infoset_for(t, node, moves, count);
    int32_t start = t.isets[infoset].start;
    int32_t first = (int32_t)t.nodes.size();
    int engine_leaves = 0;
    std::vector<double> child_values(count);
    for (int k = 0; k < count; ++k) {
        Pos child = t.nodes[node].pos;
        make(child, moves[k]);
        int32_t c = add_node(t, child, node, moves[k], t.nodes[node].depth + 1, t.nodes[node].root_J, 0, start + k);
        Node& cn = t.nodes[c];
        Node& pn = t.nodes[node];
        cn.prev_iset[OURS] = pn.prev_iset[OURS]; cn.prev_slot[OURS] = pn.prev_slot[OURS];
        cn.prev_iset[THEIRS] = pn.prev_iset[THEIRS]; cn.prev_slot[THEIRS] = pn.prev_slot[THEIRS];
        cn.prev_iset[actor] = infoset; cn.prev_slot[actor] = start + k;
        double v;
        if (wins(child)) { cn.flags |= TERMINAL; v = cn.actor == OURS ? 1.0 : -1.0; }
        else {
            auto it = values.find(to_uci(moves[k]));
            if (it != values.end()) { v = sign * it->second; ++engine_leaves; }
            else v = heuristic(t, child);
        }
        cn.leaf = (float)v;
        child_values[k] = v;
    }
    Node& n = t.nodes[node];
    n.first_child = first; n.n_children = (uint16_t)count; n.flags |= EXPANDED; n.infoset = infoset;
    Infoset& is = t.isets[infoset];
    is.nodes.push_back(node);
    if (is.nodes.size() == 1) {
        // a new infoset starts on the child Stockfish likes best (C.5)
        std::vector<double> initial(count, 0.0);
        int best = 0;
        for (int k = 1; k < count; ++k) if (sign * child_values[k] > sign * child_values[best]) best = k;
        initial[best] = 1.0;
        t.sides[actor].add(infoset, moves, count, initial.data());
    }
    // a fresh root's alternate value: min{v~(h), v*} (Fig. 9, line 14)
    if (n.depth == 0 && n.root_J >= 0 && t.fresh_J[n.root_J] && t.have_v_star) {
        double best = -2;
        for (double v : child_values) best = std::max(best, v);
        t.alt[n.root_J] = std::min(best, t.v_star);
    }
    return engine_leaves;
}

static void finish_gadget(Tree& t) {
    size_t m = t.alt.size();
    t.alpha.assign(m, 0);
    double wsum = 0, ysum = 0;
    for (size_t j = 0; j < m; ++j) { wsum += t.J_weight[j]; ysum += t.y_blueprint[j]; }
    for (size_t j = 0; j < m; ++j) {
        double uniform = wsum > 0 ? t.J_weight[j] / wsum : (m ? 1.0 / (double)m : 0);
        t.alpha[j] = ysum > 0 ? 0.5 * t.y_blueprint[j] / ysum + 0.5 * uniform : uniform;
    }
    t.res_regret.assign(2 * m, 0); t.res_strategy.assign(2 * m, 0);
    for (size_t j = 0; j < m; ++j) t.res_strategy[2 * j] = 1.0;
    t.mm_regret.assign(m, 0); t.mm_strategy.assign(m, m ? 1.0 / (double)m : 0);
    t.pmax = 1.0;
    t.gadget_ready = true;
    t.roots_of_J.assign(m, {});
    for (size_t i = 0; i < t.nodes.size(); ++i) if (t.nodes[i].parent < 0 && t.nodes[i].root_J >= 0) t.roots_of_J[t.nodes[i].root_J].push_back((int32_t)i);
}

// Predictive regret matching+ over one player's slots.
static void rm_update(Tree& t, int player) {
    Side& s = t.sides[player];
    size_t n = s.size();
    std::vector<double> expected(t.isets.size(), 0);
    for (size_t k = 0; k < n; ++k) expected[s.slot_infoset[k]] += s.strategy[k] * s.cfv[k];
    std::vector<double> total(t.isets.size(), 0);
    std::vector<double> next(n);
    for (size_t k = 0; k < n; ++k) {
        double instant = s.cfv[k] - expected[s.slot_infoset[k]];
        s.regret[k] = std::max(s.regret[k] + instant, 0.0);
        next[k] = std::max(s.regret[k] + instant, 0.0);
        total[s.slot_infoset[k]] += next[k];
    }
    for (size_t k = 0; k < n; ++k) {
        double tot = total[s.slot_infoset[k]];
        if (tot > 0) s.strategy[k] = next[k] / tot;
    }
}

static void gadget_weights(Tree& t) {
    size_t m = t.alt.size();
    t.piJ.assign(m, 0); t.fJ.assign(m, 0);
    for (size_t j = 0; j < m; ++j) {
        t.piJ[j] = t.pmax * t.alpha[j] * t.res_strategy[2 * j] + (1.0 - t.pmax) * t.mm_strategy[j];
        t.fJ[j] = t.pmax * t.alpha[j] + (1.0 - t.pmax);
    }
}

// One pass: reach probabilities top-down, values bottom-up. Node order is topological.
static void pass(Tree& t) {
    size_t N = t.nodes.size();
    size_t m = t.alt.size();
    t.reach_x.assign(N, 1); t.reach_y.assign(N, 1); t.f_ours.assign(N, 0); t.f_theirs.assign(N, 0);
    t.val.resize(N);
    std::vector<double> p_total(m, 0);
    for (size_t i = 0; i < N; ++i) if (t.nodes[i].parent < 0 && t.nodes[i].root_J >= 0) p_total[t.nodes[i].root_J] += t.nodes[i].root_p;
    const Side& x = t.sides[OURS];
    const Side& y = t.sides[THEIRS];
    for (size_t i = 0; i < N; ++i) {
        const Node& n = t.nodes[i];
        if (n.parent < 0) {
            double pn = p_total[n.root_J] > 0 ? n.root_p / p_total[n.root_J] : 0;
            t.f_ours[i] = t.piJ[n.root_J] * pn;
            t.f_theirs[i] = t.fJ[n.root_J] * pn;
        } else {
            const Node& p = t.nodes[n.parent];
            t.f_ours[i] = t.f_ours[n.parent]; t.f_theirs[i] = t.f_theirs[n.parent];
            t.reach_x[i] = t.reach_x[n.parent] * (p.actor == OURS ? x.strategy[n.slot] : 1.0);
            t.reach_y[i] = t.reach_y[n.parent] * (p.actor == THEIRS ? y.strategy[n.slot] : 1.0);
        }
    }
    for (size_t i = N; i-- > 0;) {
        const Node& n = t.nodes[i];
        if (!(n.flags & EXPANDED)) { t.val[i] = n.leaf; continue; }
        double v = 0;
        const Side& s = t.sides[n.actor];
        for (int k = 0; k < n.n_children; ++k) {
            const Node& c = t.nodes[n.first_child + k];
            v += s.strategy[c.slot] * t.val[n.first_child + k];
        }
        t.val[i] = v;
    }
}

static void counterfactual(Tree& t, int player) {
    Side& s = t.sides[player];
    std::fill(s.cfv.begin(), s.cfv.end(), 0.0);
    std::vector<double> cfreach(t.isets.size(), 0);
    double sign = player == OURS ? 1.0 : -1.0;
    for (size_t i = 0; i < t.nodes.size(); ++i) {
        const Node& n = t.nodes[i];
        if (!(n.flags & EXPANDED) || n.actor != player) continue;
        double w = (player == OURS ? t.f_ours[i] * t.reach_y[i] : t.f_theirs[i] * t.reach_x[i]);
        cfreach[n.infoset] += w;
        for (int k = 0; k < n.n_children; ++k) {
            const Node& c = t.nodes[n.first_child + k];
            s.cfv[c.slot] += w * sign * t.val[n.first_child + k];
        }
    }
    for (size_t k = 0; k < s.size(); ++k) {
        double r = cfreach[s.slot_infoset[k]];
        s.u[k] = r > 0 ? s.cfv[k] / r : s.cfv[k];
    }
}

static void iterate(Tree& t) {
    if (!t.gadget_ready) finish_gadget(t);
    gadget_weights(t);
    pass(t);
    if (t.sides[OURS].size()) { counterfactual(t, OURS); rm_update(t, OURS); pass(t); }
    if (t.sides[THEIRS].size()) { counterfactual(t, THEIRS); rm_update(t, THEIRS); }
    size_t m = t.alt.size();
    t.V.assign(m, 0);
    std::vector<double> p_total(m, 0);
    for (size_t i = 0; i < t.nodes.size(); ++i) { const Node& n = t.nodes[i]; if (n.parent < 0 && n.root_J >= 0) p_total[n.root_J] += n.root_p; }
    for (size_t i = 0; i < t.nodes.size(); ++i) {
        const Node& n = t.nodes[i];
        if (n.parent < 0 && n.root_J >= 0 && p_total[n.root_J] > 0) t.V[n.root_J] += n.root_p / p_total[n.root_J] * t.val[i];
    }
    // the gadget's regret matching: enter/exit per J (Resolve), pick J (Maxmargin)
    double mm_expected = 0;
    for (size_t j = 0; j < m; ++j) mm_expected += t.mm_strategy[j] * (t.alt[j] - t.V[j]);
    double mm_total = 0;
    std::vector<double> mm_next(m);
    for (size_t j = 0; j < m; ++j) {
        double u_enter = -t.V[j], u_exit = -t.alt[j];
        double expected = t.res_strategy[2 * j] * u_enter + t.res_strategy[2 * j + 1] * u_exit;
        double r0 = std::max(t.res_regret[2 * j] + (u_enter - expected), 0.0);
        double r1 = std::max(t.res_regret[2 * j + 1] + (u_exit - expected), 0.0);
        t.res_regret[2 * j] = r0; t.res_regret[2 * j + 1] = r1;
        double n0 = std::max(r0 + (u_enter - expected), 0.0), n1 = std::max(r1 + (u_exit - expected), 0.0);
        if (n0 + n1 > 0) { t.res_strategy[2 * j] = n0 / (n0 + n1); t.res_strategy[2 * j + 1] = n1 / (n0 + n1); }
        double instant = (t.alt[j] - t.V[j]) - mm_expected;
        t.mm_regret[j] = std::max(t.mm_regret[j] + instant, 0.0);
        mm_next[j] = std::max(t.mm_regret[j] + instant, 0.0);
        mm_total += mm_next[j];
    }
    if (mm_total > 0) for (size_t j = 0; j < m; ++j) t.mm_strategy[j] = mm_next[j] / mm_total;
    t.pmax = 0;
    for (size_t j = 0; j < m; ++j) t.pmax = std::max(t.pmax, t.res_strategy[2 * j]);
    t.has_pass = true;
    ++t.iterations;
    if (t.track_stability && t.root_infoset >= 0) {
        const Infoset& is = t.isets[t.root_infoset];
        if (t.stable.size() != is.n) t.stable.assign(is.n, 1);
        for (int k = 0; k < is.n; ++k) if (!(t.sides[OURS].strategy[is.start + k] > 0)) t.stable[k] = 0;
    }
}

static double tree_value(const Tree& t) {
    double total = 0, v = 0;
    for (size_t j = 0; j < t.V.size(); ++j) { total += t.piJ[j]; v += t.piJ[j] * t.V[j]; }
    if (total <= 0) { if (t.V.empty()) return 0; double s = 0; for (double x : t.V) s += x; return s / (double)t.V.size(); }
    return v / total;
}

// One expansion walk under the one-sided profile (C.4); -1 if it ends on a terminal node.
static int32_t walk(Tree& t, int exploring) {
    size_t m = t.alt.size();
    if (!m) return -1;
    double total = 0;
    for (size_t j = 0; j < m; ++j) total += t.piJ[j];
    double r = t.rng.uniform() * (total > 0 ? total : (double)m), acc = 0;
    size_t J = m - 1;
    for (size_t j = 0; j < m; ++j) { acc += total > 0 ? t.piJ[j] : 1.0; if (r < acc) { J = j; break; } }
    const std::vector<int32_t>& roots = t.roots_of_J[J];
    if (roots.empty()) return -1;
    double wsum = 0;
    for (int32_t n : roots) wsum += t.nodes[n].root_p;
    int32_t node = roots.back();
    r = t.rng.uniform() * wsum; acc = 0;
    for (int32_t n : roots) { acc += t.nodes[n].root_p; if (r < acc) { node = n; break; } }
    std::vector<double> probs;
    while (t.nodes[node].flags & EXPANDED) {
        const Node& n = t.nodes[node];
        int actor = n.actor;
        Side& s = t.sides[actor];
        int32_t start = t.isets[n.infoset].start;
        int count = n.n_children;
        probs.assign(count, 0);
        if (actor == exploring) {
            int support = 0;
            for (int k = 0; k < count; ++k) if (s.strategy[start + k] > 0) ++support;
            for (int k = 0; k < count; ++k) probs[k] = support ? (s.strategy[start + k] > 0 ? 0.5 / support : 0) : 0.5 / count;
            Infoset& is = t.isets[n.infoset];
            double sqrtN = std::sqrt((double)is.visits);
            int best = 0; double best_q = -1e9;
            for (int k = 0; k < count; ++k) {
                size_t sl = start + k;
                double u = s.u[sl];
                s.u_count[sl] += 1; s.u_sum[sl] += u; s.u_sq[sl] += u * u;
                double mean = s.u_sum[sl] / s.u_count[sl];
                double var = std::max(s.u_sq[sl] / s.u_count[sl] - mean * mean, 0.0);
                double q = u + PUCT_C * std::sqrt(var) * sqrtN / (1.0 + s.visits[sl]);
                if (q > best_q) { best_q = q; best = k; }
            }
            probs[best] += 0.5;
            is.visits += 1;
        } else {
            double tot = 0;
            for (int k = 0; k < count; ++k) tot += s.strategy[start + k];
            for (int k = 0; k < count; ++k) probs[k] = tot > 0 ? s.strategy[start + k] / tot : 1.0 / count;
        }
        r = t.rng.uniform(); acc = 0;
        int a = count - 1;
        for (int k = 0; k < count; ++k) { acc += probs[k]; if (r < acc) { a = k; break; } }
        if (actor == exploring) s.visits[start + a] += 1;
        node = n.first_child + a;
    }
    return (t.nodes[node].flags & TERMINAL) ? -1 : node;
}

static std::vector<int32_t> choose_leaves(Tree& t, int count, int exploring) {
    std::vector<int32_t> out;
    if (!t.gadget_ready || !t.has_pass) {
        for (size_t i = 0; i < t.nodes.size() && (int)out.size() < count; ++i)
            if (t.nodes[i].parent < 0 && !(t.nodes[i].flags & (EXPANDED | TERMINAL))) out.push_back((int32_t)i);
        return out;
    }
    std::unordered_set<int32_t> seen;
    for (int tries = 0; tries < count * 3 && (int)out.size() < count; ++tries) {
        int32_t n = walk(t, exploring);
        if (n >= 0 && seen.insert(n).second) out.push_back(n);
    }
    return out;
}

// Carry-over (Fig. 9): the new turn's roots are the old tree's nodes two plies below the
// roots of our infoset: after `played` and a reply. Those that show us `obs` are ours; the
// others with the same opponent view and history are KLUSS roots.
struct Candidate { int32_t node; bool in_I; double weight; double y_b; int32_t slot_b; };

static Tree* carry_over(Tree& old, Move played, const std::string& obs, const std::vector<Move>& our_moves, size_t max_kluss, size_t max_roots) {
    Tree* fresh = new Tree();
    fresh->side = old.side; fresh->rng = old.rng; fresh->fullmove = old.fullmove;
    set_root_view(*fresh, obs, our_moves);
    if (!old.has_pass || old.root_infoset < 0) return fresh;
    const Infoset& root_is = old.isets[old.root_infoset];
    int played_k = -1;
    for (int k = 0; k < root_is.n; ++k) if (old.sides[OURS].slot_move[root_is.start + k] == played) played_k = k;
    if (played_k < 0) return fresh;
    const Side& x = old.sides[OURS];
    const Side& y = old.sides[THEIRS];
    std::vector<Move> our_sorted = our_moves;
    std::unordered_map<std::string, std::vector<Candidate>> groups;
    std::vector<std::string> order;
    for (int32_t root : root_is.nodes) {
        const Node& rn = old.nodes[root];
        if (!(rn.flags & EXPANDED)) continue;
        for (int a = 0; a < rn.n_children; ++a) {
            int32_t child = rn.first_child + a;
            const Node& cn = old.nodes[child];
            if (!(cn.flags & EXPANDED) || (cn.flags & TERMINAL)) continue;
            double x_a = x.strategy[root_is.start + a];
            bool is_played = a == played_k;
            if (!is_played && x_a <= 0) continue;
            int32_t J_old = cn.infoset;
            for (int b = 0; b < cn.n_children; ++b) {
                int32_t grand = cn.first_child + b;
                const Node& gn = old.nodes[grand];
                if (gn.flags & TERMINAL) continue;
                bool in_I = is_played && observation(gn.pos, old.side) == obs;
                if (in_I) {
                    Move moves[MAX_MOVES];
                    int count = gen_moves(gn.pos, moves);
                    bool all = true;
                    for (Move m : our_moves) if (std::find(moves, moves + count, m) == moves + count) { all = false; break; }
                    if (!all) continue;
                    if (gn.flags & EXPANDED) {   // expanded with the moves it had; must be exactly ours
                        const Infoset& gis = old.isets[gn.infoset];
                        bool same = gis.n == (int)our_moves.size();
                        for (int k = 0; same && k < gis.n; ++k) if (x.slot_move[gis.start + k] != our_moves[k]) same = false;
                        if (!same) continue;
                    }
                }
                double weight = old.f_theirs[root] * (is_played ? 1.0 : x_a);
                if (weight <= 0) continue;
                std::string key = std::to_string(J_old) + ":" + std::to_string(b) + ":" + observation(gn.pos, old.side ^ 1);
                if (!groups.count(key)) order.push_back(key);
                int32_t slot_b = old.isets[J_old].start + b;
                groups[key].push_back({grand, in_I, weight, y.strategy[slot_b], slot_b});
            }
        }
    }
    // our heaviest nodes, up to max_roots
    std::vector<std::pair<double, int32_t>> ours;
    for (auto& kv : groups) for (const Candidate& c : kv.second) if (c.in_I) ours.push_back({-c.weight, c.node});
    std::sort(ours.begin(), ours.end());
    std::unordered_set<int32_t> allowed;
    for (size_t i = 0; i < ours.size() && i < max_roots; ++i) allowed.insert(ours[i].second);
    size_t kluss_budget = max_kluss;
    std::vector<std::pair<int32_t, std::pair<int32_t, double>>> chosen;  // node -> (J, p)
    for (const std::string& key : order) {
        std::vector<Candidate>& cands = groups[key];
        std::vector<Candidate> keep, others;
        for (const Candidate& c : cands) { if (c.in_I && allowed.count(c.node)) keep.push_back(c); else if (!c.in_I) others.push_back(c); }
        if (keep.empty()) continue;
        std::sort(others.begin(), others.end(), [](const Candidate& a, const Candidate& b) { return a.weight > b.weight; });
        for (const Candidate& c : others) { if (!kluss_budget) break; keep.push_back(c); --kluss_budget; }
        double wsum = 0, vsum = 0;
        for (const Candidate& c : keep) { wsum += c.weight; vsum += c.weight * old.val[c.node]; }
        double u_J = wsum > 0 ? vsum / wsum : 0;
        // the gift: what the opponent gave up at its root infoset by the reply that led here (C.2)
        int32_t J_old = std::stoi(key.substr(0, key.find(':')));
        const Infoset& jis = old.isets[J_old];
        double u_Jold = 0;
        for (int k = 0; k < jis.n; ++k) u_Jold += y.strategy[jis.start + k] * (-y.u[jis.start + k]);
        double gift = std::max(0.0, u_Jold - (-y.u[keep[0].slot_b]));
        int32_t Jnew = new_J(*fresh, u_J - gift, keep[0].y_b, 1.0, false);
        for (const Candidate& c : keep) chosen.push_back({c.node, {Jnew, c.weight}});
    }
    if (chosen.empty()) return fresh;
    // copy the chosen subtrees, parents before children (old index order is topological)
    std::unordered_map<int32_t, std::pair<int32_t, double>> root_of;
    for (auto& ch : chosen) root_of[ch.first] = ch.second;
    std::vector<int32_t> stack, order_nodes;
    std::vector<char> keep_mark(old.nodes.size(), 0);
    for (auto& ch : chosen) { stack.push_back(ch.first); keep_mark[ch.first] = 1; }
    while (!stack.empty()) {
        int32_t n = stack.back(); stack.pop_back();
        order_nodes.push_back(n);
        const Node& on = old.nodes[n];
        if (on.flags & EXPANDED) for (int k = 0; k < on.n_children; ++k) { int32_t c = on.first_child + k; keep_mark[c] = 1; stack.push_back(c); }
    }
    std::sort(order_nodes.begin(), order_nodes.end());
    std::unordered_map<int32_t, int32_t> mapping, iset_map;
    for (int32_t n : order_nodes) {
        const Node& on = old.nodes[n];
        bool is_root = root_of.count(n) != 0;
        int32_t parent = is_root ? -1 : mapping[on.parent];
        int depth = is_root ? 0 : fresh->nodes[parent].depth + 1;
        int32_t J = is_root ? root_of[n].first : fresh->nodes[parent].root_J;
        float p = is_root ? (float)root_of[n].second : 0.0f;
        int32_t node = add_node(*fresh, on.pos, parent, is_root ? 0 : on.move, depth, J, p, -1);
        mapping[n] = node;
        if (is_root) fresh->root_hashes.insert(hash_state(on.pos));
        Node& nn = fresh->nodes[node];
        nn.flags = on.flags & TERMINAL; nn.leaf = on.leaf;
    }
    for (int32_t n : order_nodes) {
        const Node& on = old.nodes[n];
        if (!(on.flags & EXPANDED)) continue;
        int32_t node = mapping[n];
        int actor = on.actor;
        int32_t old_iset = on.infoset;
        const Infoset& ois = old.isets[old_iset];
        if (!iset_map.count(old_iset)) {
            Infoset is; is.player = (uint8_t)actor; is.start = (int32_t)fresh->sides[actor].size(); is.n = ois.n;
            fresh->isets.push_back(is);
            int32_t id = (int32_t)fresh->isets.size() - 1;
            iset_map[old_iset] = id;
            Side& ns = fresh->sides[actor];
            const Side& os = old.sides[actor];
            std::vector<Move> moves(ois.n);
            std::vector<double> initial(ois.n);
            for (int k = 0; k < ois.n; ++k) { moves[k] = os.slot_move[ois.start + k]; initial[k] = os.strategy[ois.start + k]; }
            ns.add(id, moves.data(), ois.n, initial.data());
            for (int k = 0; k < ois.n; ++k) {
                size_t src = ois.start + k, dst = is.start + k;
                ns.regret[dst] = os.regret[src]; ns.visits[dst] = os.visits[src];
                ns.u_count[dst] = os.u_count[src]; ns.u_sum[dst] = os.u_sum[src]; ns.u_sq[dst] = os.u_sq[src];
            }
            Node& nn = fresh->nodes[node];
            std::string key = key_of(*fresh, nn, actor, moves.data(), ois.n);
            fresh->iset_key[key] = id;
            if (actor == OURS && nn.depth == 0 && nn.prev_iset[OURS] < 0 && is_root_view_node(*fresh, nn)) fresh->root_infoset = id;
        }
        int32_t id = iset_map[old_iset];
        Node& nn = fresh->nodes[node];
        nn.infoset = id; nn.flags |= EXPANDED;
        fresh->isets[id].nodes.push_back(node);
        int32_t start = fresh->isets[id].start;
        int32_t first = mapping[on.first_child];
        nn.first_child = first; nn.n_children = on.n_children;
        for (int k = 0; k < on.n_children; ++k) {
            Node& cn = fresh->nodes[first + k];
            cn.slot = start + k;
            cn.prev_iset[OURS] = nn.prev_iset[OURS]; cn.prev_slot[OURS] = nn.prev_slot[OURS];
            cn.prev_iset[THEIRS] = nn.prev_iset[THEIRS]; cn.prev_slot[THEIRS] = nn.prev_slot[THEIRS];
            cn.prev_iset[actor] = id; cn.prev_slot[actor] = start + k;
        }
    }
    return fresh;
}

// Fresh roots from the belief set S: ours to move, allowing our moves, not already roots.
static int fill(Tree& t, size_t wanted, size_t attacked_weight_x100) {
    size_t count = 0, present = 0;
    for (const Node& n : t.nodes) if (n.parent < 0) ++present;
    std::vector<uint32_t> order(S.states.size());
    std::iota(order.begin(), order.end(), 0u);
    for (size_t i = order.size(); i > 1; --i) std::swap(order[i - 1], order[t.rng.below(i)]);
    for (uint32_t idx : order) {
        if (present + count >= wanted) break;
        const Pos& p = S.states[idx];
        if (actor_of(t, p) != OURS || wins(p)) continue;
        if (t.root_hashes.count(hash_state(p))) continue;
        Move moves[MAX_MOVES];
        int n = gen_moves(p, moves);
        bool all = true;
        for (Move m : t.root_moves) if (std::find(moves, moves + n, m) == moves + n) { all = false; break; }
        if (!all) continue;
        U64 king = p.bb[KING] & p.occ[t.side];
        bool attacked = king && attacked_by(p, t.side ^ 1, msb(king));
        int32_t J = new_J(t, NEVER_EXIT, 0.0, attacked ? attacked_weight_x100 / 100.0 : 1.0, true);
        add_root(t, p, J, 1.0f);
        ++count;
    }
    return (int)count;
}

}  // namespace tree
