// The set of positions consistent with everything we have seen (Obscuro's P), kept in
// full rather than as a sample of a few hundred, which is all Python has time for.
//
// A helper process: the bot (fow/obscuro/position_set.py) writes one command per line on
// stdin and reads the answer on stdout. Every answer is one line, or a header line that
// says how many lines follow. Nothing here decides a move; it only keeps the set.
//
// The rules are the referee's (starter/referee.py), which are python-chess's pseudo-legal
// moves: no check restrictions, castling without any attack test, kings can be captured.
// A side sees its own squares and every square one of its pieces could move to. The
// tests compare this file with the referee move for move; "selftest" repeats a small
// part of that wherever the helper is built.
//
// Build: g++ -O2 -std=c++17 -o positions positions.cpp

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

typedef uint64_t U64;

enum { PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING };
enum { BLACK = 0, WHITE = 1 };
enum { WK = 1, WQ = 2, BK = 4, BQ = 8 };  // castling rights: white h-side, a-side, black h-side, a-side

static const U64 FILE_A = 0x0101010101010101ULL, FILE_H = 0x8080808080808080ULL;
static const U64 RANK3 = 0xFFULL << 16, RANK4 = 0xFFULL << 24, RANK5 = 0xFFULL << 32, RANK6 = 0xFFULL << 40;
static const char SYMBOLS[] = "pnbrqk";

static inline int lsb(U64 b) { return __builtin_ctzll(b); }
static inline int msb(U64 b) { return 63 - __builtin_clzll(b); }
static inline U64 bit(int s) { return 1ULL << s; }
static inline int file_of(int s) { return s & 7; }
static inline int rank_of(int s) { return s >> 3; }

static U64 KNIGHT_ATT[64], KING_ATT[64], PAWN_ATT[2][64], RAY[8][64];
// Rays 0..3 run towards higher squares (N, E, NE, NW), 4..7 towards lower ones (S, W, SW, SE).
static const int DF[8] = {0, 1, 1, -1, 0, -1, -1, 1};
static const int DR[8] = {1, 0, 1, 1, -1, 0, -1, -1};

static void init_tables() {
    static const int JUMPS[8][2] = {{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
    for (int s = 0; s < 64; ++s) {
        int f = file_of(s), r = rank_of(s);
        U64 knight = 0, king = 0;
        for (const auto& jump : JUMPS) {
            int ff = f + jump[0], rr = r + jump[1];
            if (ff >= 0 && ff < 8 && rr >= 0 && rr < 8) knight |= bit(rr * 8 + ff);
        }
        for (int df = -1; df <= 1; ++df)
            for (int dr = -1; dr <= 1; ++dr) {
                int ff = f + df, rr = r + dr;
                if ((df || dr) && ff >= 0 && ff < 8 && rr >= 0 && rr < 8) king |= bit(rr * 8 + ff);
            }
        KNIGHT_ATT[s] = knight;
        KING_ATT[s] = king;
        U64 white = 0, black = 0;
        if (r < 7) { if (f > 0) white |= bit(s + 7); if (f < 7) white |= bit(s + 9); }
        if (r > 0) { if (f > 0) black |= bit(s - 9); if (f < 7) black |= bit(s - 7); }
        PAWN_ATT[WHITE][s] = white;
        PAWN_ATT[BLACK][s] = black;
        for (int d = 0; d < 8; ++d) {
            U64 ray = 0;
            for (int ff = f + DF[d], rr = r + DR[d]; ff >= 0 && ff < 8 && rr >= 0 && rr < 8; ff += DF[d], rr += DR[d])
                ray |= bit(rr * 8 + ff);
            RAY[d][s] = ray;
        }
    }
}

static inline U64 along(int d, int s, U64 occupied) {
    U64 squares = RAY[d][s], blockers = squares & occupied;
    if (blockers) squares ^= RAY[d][d < 4 ? lsb(blockers) : msb(blockers)];
    return squares;
}
static inline U64 rook_att(int s, U64 occ) { return along(0, s, occ) | along(1, s, occ) | along(4, s, occ) | along(5, s, occ); }
static inline U64 bishop_att(int s, U64 occ) { return along(2, s, occ) | along(3, s, occ) | along(6, s, occ) | along(7, s, occ); }

// ---------------------------------------------------------------------------------------
// A position. Two positions are the same state when everything but the clock agrees.

struct Pos {
    U64 bb[6];          // by piece type, both colours
    U64 occ[2];         // by colour
    uint16_t halfmove;  // plies since a capture or pawn move
    int8_t ep;          // the square a pawn has just skipped, or -1; set after every double step
    uint8_t turn;
    uint8_t castling;
};

static inline bool same_state(const Pos& a, const Pos& b) {
    return !memcmp(a.bb, b.bb, sizeof a.bb) && !memcmp(a.occ, b.occ, sizeof a.occ) &&
           a.turn == b.turn && a.castling == b.castling && a.ep == b.ep;
}

static inline U64 hash_state(const Pos& p) {
    U64 h = 0x9E3779B97F4A7C15ULL;
    for (int i = 0; i < 6; ++i) { h ^= p.bb[i]; h *= 0xFF51AFD7ED558CCDULL; h ^= h >> 33; }
    h ^= p.occ[WHITE]; h *= 0xC4CEB9FE1A85EC53ULL; h ^= h >> 29;
    h ^= ((U64)p.turn << 20) | ((U64)p.castling << 8) | (U64)(uint8_t)p.ep;
    h *= 0xFF51AFD7ED558CCDULL; h ^= h >> 32;
    return h;
}

static inline int piece_on(const Pos& p, int s) {
    U64 b = bit(s);
    for (int t = 0; t < 6; ++t) if (p.bb[t] & b) return t;
    return -1;
}

// ---------------------------------------------------------------------------------------
// Moves, in the order python-chess generates them.

typedef uint16_t Move;  // from | to << 6 | promotion piece << 12 (0: none). Castling: the king's two-file move.
static inline Move mk(int from, int to, int promotion = 0) { return (Move)(from | (to << 6) | (promotion << 12)); }
static const int MAX_MOVES = 512;

static inline bool may_castle(const Pos& p, int side, bool h_side) {
    int rank = side == WHITE ? 0 : 7, base = rank * 8;
    U64 all = p.occ[0] | p.occ[1];
    if (!(p.bb[KING] & p.occ[side] & bit(base + 4))) return false;
    int right = side == WHITE ? (h_side ? WK : WQ) : (h_side ? BK : BQ);
    if (!(p.castling & right)) return false;
    if (!(p.bb[ROOK] & p.occ[side] & bit(base + (h_side ? 7 : 0)))) return false;
    U64 between = h_side ? (bit(base + 5) | bit(base + 6)) : (bit(base + 1) | bit(base + 2) | bit(base + 3));
    return !(all & between);  // and no test for attacks on the way: that is the Fog of War rule
}

static inline void add_pawn_move(Move* out, int& n, int from, int to) {
    if (rank_of(to) == 0 || rank_of(to) == 7) {
        out[n++] = mk(from, to, QUEEN); out[n++] = mk(from, to, ROOK);
        out[n++] = mk(from, to, BISHOP); out[n++] = mk(from, to, KNIGHT);
    } else {
        out[n++] = mk(from, to);
    }
}

static int gen_moves(const Pos& p, Move* out) {
    int n = 0, us = p.turn, them = us ^ 1;
    U64 own = p.occ[us], enemy = p.occ[them], all = own | enemy;
    for (U64 pieces = own & ~p.bb[PAWN]; pieces;) {
        int from = msb(pieces);
        U64 fb = bit(from), targets;
        pieces ^= fb;
        if (p.bb[KNIGHT] & fb) targets = KNIGHT_ATT[from];
        else if (p.bb[KING] & fb) targets = KING_ATT[from];
        else {
            targets = 0;
            if ((p.bb[BISHOP] | p.bb[QUEEN]) & fb) targets = bishop_att(from, all);
            if ((p.bb[ROOK] | p.bb[QUEEN]) & fb) targets |= rook_att(from, all);
        }
        for (targets &= ~own; targets;) { int to = msb(targets); targets ^= bit(to); out[n++] = mk(from, to); }
    }
    if (p.bb[KING]) {
        int king = (us == WHITE ? 0 : 56) + 4;
        if (may_castle(p, us, true)) out[n++] = mk(king, king + 2);
        if (may_castle(p, us, false)) out[n++] = mk(king, king - 2);
    }
    U64 pawns = p.bb[PAWN] & own;
    if (!pawns) return n;
    for (U64 capturers = pawns; capturers;) {
        int from = msb(capturers);
        capturers ^= bit(from);
        for (U64 targets = PAWN_ATT[us][from] & enemy; targets;) { int to = msb(targets); targets ^= bit(to); add_pawn_move(out, n, from, to); }
    }
    U64 single, twice;
    if (us == WHITE) { single = (pawns << 8) & ~all; twice = (single << 8) & ~all & (RANK3 | RANK4); }
    else { single = (pawns >> 8) & ~all; twice = (single >> 8) & ~all & (RANK6 | RANK5); }
    for (U64 b = single; b;) { int to = msb(b); b ^= bit(to); add_pawn_move(out, n, to + (us == BLACK ? 8 : -8), to); }
    for (U64 b = twice; b;) { int to = msb(b); b ^= bit(to); out[n++] = mk(to + (us == BLACK ? 16 : -16), to); }
    if (p.ep > 0 && !(bit(p.ep) & all))
        for (U64 capturers = pawns & PAWN_ATT[them][p.ep] & (us == WHITE ? RANK5 : RANK4); capturers;) {
            int from = msb(capturers);
            capturers ^= bit(from);
            out[n++] = mk(from, p.ep);
        }
    return n;
}

static inline int corner_right(int s) { return s == 7 ? WK : s == 0 ? WQ : s == 63 ? BK : s == 56 ? BQ : 0; }

// Plays a move that gen_moves produced for this position (python-chess's push).
static void make(Pos& p, Move m) {
    int from = m & 63, to = (m >> 6) & 63, promotion = m >> 12;
    int us = p.turn, them = us ^ 1;
    U64 fb = bit(from), tb = bit(to);
    int skipped = p.ep;
    p.ep = -1;
    if (p.halfmove < 60000) ++p.halfmove;
    int piece = piece_on(p, from);
    if (piece == KING && from == (us == WHITE ? 4 : 60) && (to == from + 2 || to == from - 2)) {
        int base = us == WHITE ? 0 : 56;
        U64 rook = to > from ? (bit(base + 7) | bit(base + 5)) : (bit(base) | bit(base + 3));
        p.bb[KING] ^= fb | tb;
        p.bb[ROOK] ^= rook;
        p.occ[us] ^= fb | tb | rook;
        p.castling &= us == WHITE ? ~(WK | WQ) : ~(BK | BQ);
        p.turn = (uint8_t)them;
        return;
    }
    int captured = piece_on(p, to);
    if (piece == PAWN || captured >= 0) p.halfmove = 0;
    p.bb[piece] ^= fb;
    p.occ[us] ^= fb;
    p.castling &= ~(corner_right(from) | corner_right(to));
    if (piece == KING) p.castling &= us == WHITE ? ~(WK | WQ) : ~(BK | BQ);
    else if (captured == KING) {
        if (us == WHITE && rank_of(to) == 7) p.castling &= ~(BK | BQ);
        else if (us == BLACK && rank_of(to) == 0) p.castling &= ~(WK | WQ);
    }
    if (piece == PAWN) {
        int step = to - from;
        if (step == 16 && rank_of(from) == 1) p.ep = (int8_t)(from + 8);
        else if (step == -16 && rank_of(from) == 6) p.ep = (int8_t)(from - 8);
        else if (to == skipped && captured < 0 && (step == 7 || step == 9 || step == -7 || step == -9)) {
            int square = skipped + (us == WHITE ? -8 : 8);  // en passant: the pawn that skipped is taken
            int victim = piece_on(p, square);
            if (victim >= 0) { p.bb[victim] ^= bit(square); p.occ[(p.occ[WHITE] & bit(square)) ? WHITE : BLACK] ^= bit(square); }
        }
    }
    if (captured >= 0) { p.bb[captured] ^= tb; p.occ[(p.occ[WHITE] & tb) ? WHITE : BLACK] ^= tb; }
    p.bb[promotion ? promotion : piece] |= tb;
    p.occ[us] |= tb;
    p.turn = (uint8_t)them;
}

static inline bool attacked_by(const Pos& p, int color, int s) {
    U64 all = p.occ[0] | p.occ[1];
    U64 attackers = (KING_ATT[s] & p.bb[KING]) | (KNIGHT_ATT[s] & p.bb[KNIGHT]) |
                    (rook_att(s, all) & (p.bb[QUEEN] | p.bb[ROOK])) |
                    (bishop_att(s, all) & (p.bb[QUEEN] | p.bb[BISHOP])) |
                    (PAWN_ATT[color ^ 1][s] & p.bb[PAWN]);
    return (attackers & p.occ[color]) != 0;
}

// The side to move can take the other king (or it is gone): the game is over already.
static inline bool wins(const Pos& p) {
    U64 king = p.occ[p.turn ^ 1] & p.bb[KING];
    return !king || attacked_by(p, p.turn, msb(king));
}

// What `side` sees: its own squares and every square one of its pieces could move to.
static U64 visible_to(const Pos& p, int side) {
    int them = side ^ 1;
    U64 own = p.occ[side], enemy = p.occ[them], all = own | enemy, seen = own;
    for (U64 b = p.bb[KNIGHT] & own; b; b &= b - 1) seen |= KNIGHT_ATT[lsb(b)];
    for (U64 b = p.bb[KING] & own; b; b &= b - 1) seen |= KING_ATT[lsb(b)];
    for (U64 b = (p.bb[BISHOP] | p.bb[QUEEN]) & own; b; b &= b - 1) seen |= bishop_att(lsb(b), all);
    for (U64 b = (p.bb[ROOK] | p.bb[QUEEN]) & own; b; b &= b - 1) seen |= rook_att(lsb(b), all);
    int king = (side == WHITE ? 0 : 56) + 4;
    if (may_castle(p, side, true)) seen |= bit(king + 2);
    if (may_castle(p, side, false)) seen |= bit(king - 2);
    U64 pawns = p.bb[PAWN] & own;
    if (pawns) {
        U64 attacks, single, twice;
        if (side == WHITE) {
            attacks = ((pawns << 7) & ~FILE_H) | ((pawns << 9) & ~FILE_A);
            single = (pawns << 8) & ~all; twice = (single << 8) & ~all & (RANK3 | RANK4);
        } else {
            attacks = ((pawns >> 9) & ~FILE_H) | ((pawns >> 7) & ~FILE_A);
            single = (pawns >> 8) & ~all; twice = (single >> 8) & ~all & (RANK6 | RANK5);
        }
        seen |= (attacks & enemy) | single | twice;
        // En passant counts only on our own turn, and shows the pawn it would take as well.
        if (p.turn == side && p.ep > 0 && !(bit(p.ep) & all) &&
            (pawns & PAWN_ATT[them][p.ep] & (side == WHITE ? RANK5 : RANK4)))
            seen |= bit(p.ep) | bit(p.ep + (side == WHITE ? -8 : 8));
    }
    return seen;
}

struct View {  // one observation: which squares are seen, and what is on them
    U64 visible = 0;
    U64 pieces[2][6] = {{0}};
    bool ok = false;
};

static View parse_view(const std::string& text) {
    View view;
    if (text.size() != 64) return view;
    for (int s = 0; s < 64; ++s) {
        char c = text[s];
        if (c == '?') continue;
        view.visible |= bit(s);
        if (c == '-') continue;
        const char* at = strchr(SYMBOLS, c | 0x20);
        if (!at || !*at) return view;
        view.pieces[(c & 0x20) ? BLACK : WHITE][at - SYMBOLS] |= bit(s);
    }
    view.ok = true;
    return view;
}

static inline bool same_pieces(const Pos& p, const View& view) {
    for (int t = 0; t < 6; ++t)
        if ((p.bb[t] & p.occ[WHITE] & view.visible) != view.pieces[WHITE][t] ||
            (p.bb[t] & p.occ[BLACK] & view.visible) != view.pieces[BLACK][t]) return false;
    return true;
}

static std::string observation(const Pos& p, int side) {
    U64 seen = visible_to(p, side);
    std::string text(64, '?');
    for (int s = 0; s < 64; ++s)
        if (seen & bit(s)) {
            int piece = piece_on(p, s);
            text[s] = piece < 0 ? '-' : (p.occ[WHITE] & bit(s)) ? (char)(SYMBOLS[piece] - 32) : SYMBOLS[piece];
        }
    return text;
}

// ---------------------------------------------------------------------------------------
// Text: FEN (always with the skipped square, as python-chess's en_passant="fen") and UCI.

static bool parse_fen(const std::string& fen, Pos& p, unsigned& fullmove) {
    std::istringstream in(fen);
    std::string board, turn, castling, ep;
    long half = 0, full = 1;
    if (!(in >> board >> turn)) return false;
    if (!(in >> castling)) castling = "-";
    if (!(in >> ep)) ep = "-";
    if (!(in >> half)) half = 0;
    if (!(in >> full)) full = 1;
    memset(&p, 0, sizeof p);
    int file = 0, rank = 7;
    for (char c : board) {
        if (c == '/') { if (file != 8) return false; file = 0; --rank; }
        else if (c >= '1' && c <= '8') file += c - '0';
        else {
            const char* at = strchr(SYMBOLS, c | 0x20);
            if (!at || !*at || file > 7 || rank < 0) return false;
            p.bb[at - SYMBOLS] |= bit(rank * 8 + file);
            p.occ[(c & 0x20) ? BLACK : WHITE] |= bit(rank * 8 + file);
            ++file;
        }
        if (file > 8 || rank < 0) return false;
    }
    if (rank != 0 || file != 8) return false;
    if (turn != "w" && turn != "b") return false;
    p.turn = turn == "w" ? WHITE : BLACK;
    for (char c : castling) p.castling |= c == 'K' ? WK : c == 'Q' ? WQ : c == 'k' ? BK : c == 'q' ? BQ : 0;
    // Rights only count with the king and the rook on their squares (python-chess cleans them the same way).
    for (int side = 0; side < 2; ++side) {
        int base = side == WHITE ? 0 : 56;
        bool king = p.bb[KING] & p.occ[side] & bit(base + 4);
        if (!king || !(p.bb[ROOK] & p.occ[side] & bit(base + 7))) p.castling &= side == WHITE ? ~WK : ~BK;
        if (!king || !(p.bb[ROOK] & p.occ[side] & bit(base))) p.castling &= side == WHITE ? ~WQ : ~BQ;
    }
    p.ep = -1;
    if (ep != "-") {
        if (ep.size() != 2 || ep[0] < 'a' || ep[0] > 'h' || ep[1] < '1' || ep[1] > '8') return false;
        p.ep = (int8_t)((ep[1] - '1') * 8 + (ep[0] - 'a'));
    }
    p.halfmove = (uint16_t)std::max(0L, std::min(half, 60000L));
    fullmove = (unsigned)std::max(1L, full);
    return true;
}

static std::string to_fen(const Pos& p, unsigned fullmove) {
    std::string text;
    for (int rank = 7; rank >= 0; --rank) {
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            int s = rank * 8 + file, piece = piece_on(p, s);
            if (piece < 0) { ++empty; continue; }
            if (empty) { text += (char)('0' + empty); empty = 0; }
            text += (p.occ[WHITE] & bit(s)) ? (char)(SYMBOLS[piece] - 32) : SYMBOLS[piece];
        }
        if (empty) text += (char)('0' + empty);
        if (rank) text += '/';
    }
    text += p.turn == WHITE ? " w " : " b ";
    if (!p.castling) text += '-';
    else {
        if (p.castling & WK) text += 'K';
        if (p.castling & WQ) text += 'Q';
        if (p.castling & BK) text += 'k';
        if (p.castling & BQ) text += 'q';
    }
    text += ' ';
    if (p.ep < 0) text += '-';
    else { text += (char)('a' + file_of(p.ep)); text += (char)('1' + rank_of(p.ep)); }
    text += ' ' + std::to_string(p.halfmove) + ' ' + std::to_string(fullmove);
    return text;
}

static std::string to_uci(Move m) {
    int from = m & 63, to = (m >> 6) & 63, promotion = m >> 12;
    std::string text;
    text += (char)('a' + file_of(from)); text += (char)('1' + rank_of(from));
    text += (char)('a' + file_of(to)); text += (char)('1' + rank_of(to));
    if (promotion) text += SYMBOLS[promotion];
    return text;
}

static bool parse_uci(const std::string& text, Move& m) {
    if (text.size() != 4 && text.size() != 5) return false;
    for (int i = 0; i < 4; i += 2)
        if (text[i] < 'a' || text[i] > 'h' || text[i + 1] < '1' || text[i + 1] > '8') return false;
    int promotion = 0;
    if (text.size() == 5) {
        const char* at = strchr("nbrq", text[4]);
        if (!at || !*at) return false;
        promotion = KNIGHT + (int)(at - "nbrq");
    }
    m = mk((text[1] - '1') * 8 + (text[0] - 'a'), (text[3] - '1') * 8 + (text[2] - 'a'), promotion);
    return true;
}

// ---------------------------------------------------------------------------------------
// The set.

struct Rng {  // xorshift64*: small, fast, and the same everywhere
    U64 s = 0x2545F4914F6CDD1DULL;
    void seed(U64 v) { s = v * 0x9E3779B97F4A7C15ULL + 0x632BE59BD9B4E019ULL; if (!s) s = 1; next(); next(); }
    U64 next() { s ^= s >> 12; s ^= s << 25; s ^= s >> 27; return s * 0x2545F4914F6CDD1DULL; }
    double uniform() { return (double)(next() >> 11) * (1.0 / 9007199254740992.0); }
    size_t below(size_t n) { return (size_t)(uniform() * (double)n) % n; }
};

struct Origin { uint32_t kid, parent; Move move; };
struct Table { double other = 0; std::vector<std::pair<Move, double>> odds; };

struct Index {  // finds a state among `states`, or adds it: open addressing on the state's hash
    std::vector<uint32_t> slot;
    std::vector<U64> hashes;
    size_t mask = 0;
    void reset(size_t expected) {
        size_t size = 1024;
        while (size < expected * 2) size <<= 1;
        slot.assign(size, 0);
        mask = size - 1;
        hashes.clear();
    }
    void grow(const std::vector<Pos>& states) {
        slot.assign(slot.size() * 2, 0);
        mask = slot.size() - 1;
        for (size_t i = 0; i < states.size(); ++i) {
            size_t at = hashes[i] & mask;
            while (slot[at]) at = (at + 1) & mask;
            slot[at] = (uint32_t)i + 1;
        }
    }
    uint32_t find_or_add(const Pos& p, std::vector<Pos>& states) {
        U64 h = hash_state(p);
        for (size_t at = h & mask;; at = (at + 1) & mask) {
            uint32_t entry = slot[at];
            if (!entry) {
                states.push_back(p);
                hashes.push_back(h);
                slot[at] = (uint32_t)states.size();
                if (states.size() * 2 > slot.size()) grow(states);
                return (uint32_t)states.size() - 1;
            }
            if (hashes[entry - 1] == h && same_state(states[entry - 1], p)) return entry - 1;
        }
    }
};

struct Set {
    int side = WHITE;            // our colour
    size_t cap = 100000;         // the most states kept
    double head_share = 0.75;    // of a set that is cut down, the part kept by weight
    std::vector<Pos> states;
    std::vector<double> weights;
    bool exact = true;           // false once the cap or the clock may have dropped the true position
    bool weighted = false;       // true once an opponent policy has told the states apart
    unsigned fullmove = 1;
    Rng rng;
    // What "opp" found, waiting for "commit" (the weights need the policy's answer first).
    bool pending = false;
    std::vector<Pos> kids;
    std::vector<Origin> origins;
    std::vector<uint32_t> n_moves;   // per parent
    std::vector<uint8_t> flags;      // per parent: 1 has a successor, 2 could have taken our king
    size_t expanded = 0;
    bool cut_short = false;
    double ms = 0;
};

static Set S;
typedef std::chrono::steady_clock Clock;
static inline double ms_since(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}

static void start_position(Pos& p) {
    unsigned full;
    parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", p, full);
}

// One ply on from every state: the successors that produce `view`. With `own` only that
// move is tried. Stops early when the time or the room runs out, heaviest states first.
static void expand(const View& view, bool own, Move own_move, double budget_ms) {
    Clock::time_point start = Clock::now();
    size_t n_states = S.states.size();
    S.kids.clear();
    S.origins.clear();
    S.n_moves.assign(n_states, 0);
    S.flags.assign(n_states, 0);
    S.expanded = 0;
    S.cut_short = false;
    std::vector<uint32_t> order(n_states);
    std::iota(order.begin(), order.end(), 0u);
    if (S.weighted)
        std::stable_sort(order.begin(), order.end(), [](uint32_t a, uint32_t b) { return S.weights[a] > S.weights[b]; });
    size_t room = std::max<size_t>(4 * S.cap, 50000);
    Index index;
    index.reset(std::min(room, n_states * 4));
    Move moves[MAX_MOVES];
    for (size_t i = 0; i < n_states; ++i) {
        // The clock is looked at after every 32 states, and never before the first 32.
        if (S.kids.size() >= room || (budget_ms > 0 && i && (i & 31) == 0 && ms_since(start) > budget_ms)) {
            S.cut_short = true;
            break;
        }
        uint32_t parent = order[i];
        const Pos& from = S.states[parent];
        int n = gen_moves(from, moves);
        S.n_moves[parent] = (uint32_t)n;
        if (!own && wins(from)) S.flags[parent] |= 2;
        for (int j = 0; j < n; ++j) {
            if (own && moves[j] != own_move) continue;
            Pos kid = from;
            make(kid, moves[j]);
            if (!same_pieces(kid, view) || wins(kid) || visible_to(kid, S.side) != view.visible) continue;
            S.origins.push_back({index.find_or_add(kid, S.kids), parent, moves[j]});
            S.flags[parent] |= 1;
        }
        ++S.expanded;
    }
    S.ms = ms_since(start);
}

// `size` of the states. With equal weights, a random sample. Otherwise the heaviest ones
// for the most part plus a random draw of the others, each of which then stands for the
// several that were not drawn (belief.py's _cut).
static void cut(size_t size) {
    size_t n = S.states.size();
    if (n <= size) return;
    double low = *std::min_element(S.weights.begin(), S.weights.end());
    double high = *std::max_element(S.weights.begin(), S.weights.end());
    std::vector<uint32_t> order(n);
    std::iota(order.begin(), order.end(), 0u);
    for (size_t i = n - 1; i > 0; --i) std::swap(order[i], order[S.rng.below(i + 1)]);
    std::vector<Pos> states;
    std::vector<double> weights;
    states.reserve(size);
    weights.reserve(size);
    if (high <= low * (1 + 1e-12)) {
        for (size_t i = 0; i < size; ++i) { states.push_back(S.states[order[i]]); weights.push_back(S.weights[order[i]]); }
    } else {
        std::stable_sort(order.begin(), order.end(), [](uint32_t a, uint32_t b) { return S.weights[a] > S.weights[b]; });
        size_t head = (size_t)(S.head_share * (double)size), drawn = size - head, tail = n - head;
        for (size_t i = 0; i < head; ++i) { states.push_back(S.states[order[i]]); weights.push_back(S.weights[order[i]]); }
        for (size_t i = 0; i < drawn; ++i) std::swap(order[head + i], order[head + i + S.rng.below(tail - i)]);
        double scale = (double)tail / (double)std::max<size_t>(drawn, 1);
        for (size_t i = 0; i < drawn; ++i) { states.push_back(S.states[order[head + i]]); weights.push_back(S.weights[order[head + i]] * scale); }
    }
    S.states.swap(states);
    S.weights.swap(weights);
}

static double effective_size() {
    double sum = 0, squares = 0;
    for (double w : S.weights) { sum += w; squares += w * w; }
    return squares > 0 ? sum * sum / squares : 0.0;
}

static void report(const char* word, size_t size, size_t parents, size_t kids) {
    U64 skipped = 0;
    for (const Pos& p : S.states) if (p.ep >= 0) skipped |= bit(p.ep);
    printf("%s size=%zu exact=%d weighted=%d ess=%.3f ep=%llx parents=%zu expanded=%zu kids=%zu ms=%.2f\n",
           word, size, S.exact ? 1 : 0, S.weighted ? 1 : 0, effective_size(), (unsigned long long)skipped,
           parents, S.expanded, kids, S.ms);
}

// Takes what "expand" found as the new set. `mover` is the colour that made the move.
static void adopt(std::vector<double>& weights, int mover) {
    size_t parents = S.states.size(), kids = S.kids.size();
    S.pending = false;
    if (kids == 0) {  // nothing fits: the set stays as it was, for the caller to repair
        report("ok", 0, parents, 0);
        return;
    }
    if (S.cut_short) S.exact = false;
    S.states.swap(S.kids);
    S.weights.swap(weights);
    if (mover == BLACK) ++S.fullmove;
    if (S.states.size() > S.cap) { S.exact = false; cut(S.cap); }
    report("ok", S.states.size(), parents, kids);
}

static void finish_own() {
    std::vector<double> weights(S.kids.size(), 0.0);
    for (const Origin& o : S.origins)
        weights[o.kid] = S.weighted ? weights[o.kid] + S.weights[o.parent] : std::max(weights[o.kid], S.weights[o.parent]);
    adopt(weights, S.side);
}

// Weights after a move of the opponent's (belief.py's _after_opponent). A state weighs
// what its parent weighed times the odds of the move, summed over the ways to reach it.
static void finish_opponent(bool policy, double king_miss, const std::vector<int32_t>& table_of, const std::vector<Table>& tables) {
    std::vector<double> weights(S.kids.size(), 0.0);
    bool told = false;
    if (policy)
        for (size_t parent = 0; parent < S.flags.size() && !told; ++parent)
            told = (S.flags[parent] & 1) && ((S.flags[parent] & 2) || table_of[parent] >= 0);
    S.weighted = S.weighted || told;
    if (!S.weighted) {
        for (const Origin& o : S.origins) weights[o.kid] = std::max(weights[o.kid], S.weights[o.parent]);
    } else {
        for (const Origin& o : S.origins) {
            double moves = (double)std::max<uint32_t>(S.n_moves[o.parent], 1), odds;
            if (policy && (S.flags[o.parent] & 2)) odds = king_miss / moves;
            else if (table_of[o.parent] >= 0) {
                const Table& table = tables[(size_t)table_of[o.parent]];
                odds = table.other;
                for (const auto& entry : table.odds) if (entry.first == o.move) { odds = entry.second; break; }
            } else odds = 1.0 / moves;
            weights[o.kid] += S.weights[o.parent] * odds;
        }
        double top = 0;
        for (double w : weights) top = std::max(top, w);
        for (double& w : weights) w = top > 0 ? w / top : 1.0;
    }
    adopt(weights, S.side ^ 1);
}

// The states to look at, each with the number of times it was drawn (stockfish_search.py's
// draw): without weights `n` of them at random, once each; with weights `n` draws spaced
// evenly through the total, so that a state's count is its fair share to within one.
static void sample(size_t n, std::vector<std::pair<uint32_t, double>>& out) {
    size_t size = S.states.size();
    out.clear();
    if (!size || !n) return;
    double low = *std::min_element(S.weights.begin(), S.weights.end());
    double high = *std::max_element(S.weights.begin(), S.weights.end());
    std::vector<uint32_t> order(size);
    std::iota(order.begin(), order.end(), 0u);
    for (size_t i = size - 1; i > 0; --i) std::swap(order[i], order[S.rng.below(i + 1)]);
    if (!S.weighted || high <= low * (1 + 1e-12)) {
        for (size_t i = 0; i < std::min(n, size); ++i) out.push_back({order[i], 1.0});
        return;
    }
    double total = 0;
    for (double w : S.weights) total += std::max(w, 0.0);
    double step = total / (double)n, offset = S.rng.uniform(), reached = 0;
    size_t next = 0;  // the draws are at (offset + 0, 1, 2, ...) * step
    for (size_t i = 0; i < size; ++i) {
        reached += std::max(S.weights[order[i]], 0.0);
        double count = 0;
        while (next < n && (offset + (double)next) * step < reached) { ++count; ++next; }
        if (i + 1 == size) { count += (double)(n - next); next = n; }  // rounding leaves the last ones here
        if (count > 0) out.push_back({order[i], count});
    }
    std::stable_sort(out.begin(), out.end(), [](const std::pair<uint32_t, double>& a, const std::pair<uint32_t, double>& b) { return a.second > b.second; });
}

// ---------------------------------------------------------------------------------------
// Self-test: move counts under these rules, worked out with the referee (python-chess).

static U64 count_lines(Pos& p, int depth) {
    if (depth == 0) return 1;
    Move moves[MAX_MOVES];
    int n = gen_moves(p, moves);
    if (depth == 1) return (U64)n;
    U64 total = 0;
    for (int i = 0; i < n; ++i) { Pos next = p; make(next, moves[i]); total += count_lines(next, depth - 1); }
    return total;
}

static int selftest() {
    struct Case { const char* fen; int depth; U64 expected; };
    static const Case cases[] = {
        {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 4, 197742},
        {"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 3, 98903},
        {"n1n5/PPPk4/8/8/8/8/4Kppp/5N1N b - - 0 1", 3, 13359},
        {"8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 4867},
    };
    int failures = 0;
    for (const Case& c : cases) {
        Pos p;
        unsigned full;
        U64 found = parse_fen(c.fen, p, full) ? count_lines(p, c.depth) : 0;
        if (found != c.expected) { ++failures; printf("selftest: %s depth %d: %llu, expected %llu\n", c.fen, c.depth, (unsigned long long)found, (unsigned long long)c.expected); }
    }
    Pos p;
    start_position(p);
    // (Written in pieces so that no "?" is followed by "?-", which old compilers read as one character.)
    const std::string unseen(32, '?'), empty(16, '-');
    if (observation(p, WHITE) != "RNBQKBNRPPPPPPPP" + empty + unseen ||
        observation(p, BLACK) != unseen + empty + "pppppppprnbqkbnr") {
        ++failures;
        printf("selftest: the starting position is seen wrongly\n");
    }
    Clock::time_point start = Clock::now();
    U64 nodes = count_lines(p, 5);
    printf("selftest %s: %d of 5 checks failed; %llu positions in %.0f ms\n", failures ? "FAILED" : "ok", failures,
           (unsigned long long)nodes, ms_since(start));
    return failures ? 1 : 0;
}

// ---------------------------------------------------------------------------------------
// The protocol.

static bool read_states(std::istream& in, size_t count, std::vector<Pos>& states, std::vector<double>& weights, unsigned& fullmove) {
    std::string line;
    for (size_t i = 0; i < count; ++i) {
        if (!std::getline(in, line)) return false;
        std::istringstream row(line);
        std::string tag, rest;
        double weight;
        if (!(row >> tag >> weight) || tag != "s") return false;
        std::getline(row, rest);
        Pos p;
        if (!parse_fen(rest, p, fullmove)) return false;
        states.push_back(p);
        weights.push_back(weight);
    }
    return true;
}

#include "tree.inc"
#include "engines.inc"

// The "tree" commands: see tree.inc. Python drives one search per move with them.
static void tree_command(std::istringstream& in) {
    using namespace tree;
    std::string what;
    in >> what;
    if (what == "start") {
        // tree start <w|b> <obs> <k> <uci...> <played|-> <max_roots> <max_kluss> <seed>
        std::string side, obs, played;
        unsigned long long k = 0, max_roots = 256, max_kluss = 128, seed = 0;
        in >> side >> obs >> k;
        std::vector<Move> moves;
        for (unsigned long long i = 0; i < k; ++i) { std::string u; Move m; in >> u; if (!parse_uci(u, m)) { printf("err bad move\n"); return; } moves.push_back(m); }
        in >> played >> max_roots >> max_kluss >> seed;
        if (parse_view(obs).ok == false) { printf("err bad view\n"); return; }
        Move played_move = 0;
        bool carry = played != "-" && parse_uci(played, played_move) && T != nullptr;
        Tree* fresh;
        if (carry) fresh = carry_over(*T, played_move, obs, moves, (size_t)max_kluss, (size_t)max_roots);
        else { fresh = new Tree(); fresh->side = side == "b" ? BLACK : WHITE; fresh->rng.seed(seed); set_root_view(*fresh, obs, moves); }
        fresh->side = side == "b" ? BLACK : WHITE;
        fresh->fullmove = S.fullmove;
        delete OLD; OLD = nullptr;
        delete T; T = fresh;
        size_t roots = 0; for (const Node& n : T->nodes) if (n.parent < 0) ++roots;
        printf("ok roots=%zu nodes=%zu\n", roots, T->nodes.size());
    } else if (what == "engines") {
        // tree engines <count> <hash_mb> <binary>: Stockfish processes of the helper's own
        unsigned long long count = 2, hash = 64;
        std::string binary;
        in >> count >> hash >> binary;
        int ready = engines::start(binary, (int)count, (int)hash, 8000);
        printf("ok ready=%d\n", ready);
    } else if (!T) {
        printf("err no tree\n");
    } else if (what == "fill") {
        // tree fill <wanted> <attacked_weight_x100> <v_star|none>
        unsigned long long wanted = 256, attacked = 600;
        std::string v;
        in >> wanted >> attacked >> v;
        if (v != "none" && !v.empty()) { T->v_star = atof(v.c_str()); T->have_v_star = true; }
        int added = fill(*T, (size_t)wanted, (size_t)attacked);
        size_t roots = 0; for (const Node& n : T->nodes) if (n.parent < 0) ++roots;
        printf("ok added=%d roots=%zu\n", added, roots);
    } else if (what == "leaves") {
        unsigned long long count = 16; int exploring = 0;
        in >> count >> exploring;
        std::vector<int32_t> leaves = choose_leaves(*T, (int)count, exploring);
        printf("leaves %zu\n", leaves.size());
        for (int32_t n : leaves) printf("l %d %s\n", n, to_fen(T->nodes[n].pos, T->fullmove).c_str());
    } else if (what == "children") {
        // tree children <m>, then m lines: c <node> <k> <uci> <value> ...
        unsigned long long m = 0;
        in >> m;
        int expanded = 0, engine_leaves = 0;
        std::string row;
        for (unsigned long long i = 0; i < m && std::getline(std::cin, row); ++i) {
            std::istringstream r(row);
            std::string c; long node = -1; unsigned long long k = 0;
            r >> c >> node >> k;
            std::unordered_map<std::string, double> values;
            for (unsigned long long j = 0; j < k; ++j) { std::string u; double v; r >> u >> v; values[u] = v; }
            if (node < 0 || (size_t)node >= T->nodes.size()) continue;
            if (T->nodes[node].flags & (EXPANDED | TERMINAL)) continue;
            engine_leaves += expand(*T, (int32_t)node, values);
            ++expanded;
        }
        printf("ok expanded=%d engine_leaves=%d nodes=%zu infosets=%zu root_infoset=%d\n", expanded, engine_leaves, T->nodes.size(), T->isets.size(), T->root_infoset);
    } else if (what == "expand") {
        // tree expand <k> <node...> <depth> <ms>: value and add the children of these nodes
        unsigned long long k = 0;
        in >> k;
        std::vector<int32_t> nodes;
        for (unsigned long long i = 0; i < k; ++i) { long n = -1; in >> n; if (n >= 0 && (size_t)n < T->nodes.size()) nodes.push_back((int32_t)n); }
        int depth = 1; double ms = 1000;
        in >> depth >> ms;
        std::vector<std::string> fens;
        for (int32_t n : nodes) fens.push_back(to_fen(T->nodes[n].pos, T->fullmove));
        std::vector<engines::Result> results;
        if (engines::ready_count() > 0 && !fens.empty())
            engines::evaluate(fens, depth, Clock::now() + std::chrono::milliseconds((long)ms), results);
        int expanded = 0, engine_leaves = 0;
        for (size_t i = 0; i < nodes.size(); ++i) {
            std::unordered_map<std::string, double> none;
            engine_leaves += expand(*T, nodes[i], (i < results.size() && results[i].ok) ? results[i].scores : none);
            ++expanded;
        }
        printf("ok expanded=%d engine_leaves=%d nodes=%zu infosets=%zu root_infoset=%d\n", expanded, engine_leaves, T->nodes.size(), T->isets.size(), T->root_infoset);
    } else if (what == "gadget") {
        finish_gadget(*T);
        printf("ok J=%zu\n", T->alt.size());
    } else if (what == "grow") {
        // tree grow <count> <exploring> <depth> <ms>: choose leaves, value their children with
        // the helper's engines (the heuristic where none answers), add them to the tree
        unsigned long long count = 128; int exploring = 0, depth = 1; double ms = 500;
        in >> count >> exploring >> depth >> ms;
        std::vector<int32_t> leaves = choose_leaves(*T, (int)count, exploring);
        std::vector<std::string> fens;
        for (int32_t n : leaves) fens.push_back(to_fen(T->nodes[n].pos, T->fullmove));
        std::vector<engines::Result> results;
        if (engines::ready_count() > 0 && !fens.empty())
            engines::evaluate(fens, depth, Clock::now() + std::chrono::milliseconds((long)ms), results);
        int expanded = 0, engine_leaves = 0;
        for (size_t i = 0; i < leaves.size(); ++i) {
            std::unordered_map<std::string, double> none;
            const std::unordered_map<std::string, double>& values = (i < results.size() && results[i].ok) ? results[i].scores : none;
            engine_leaves += expand(*T, leaves[i], values);
            ++expanded;
        }
        printf("ok expanded=%d engine_leaves=%d nodes=%zu infosets=%zu root_infoset=%d engines=%d\n",
               expanded, engine_leaves, T->nodes.size(), T->isets.size(), T->root_infoset, engines::ready_count());
    } else if (what == "solve") {
        double ms = 10; int stability = 0;
        in >> ms >> stability;
        if (stability) T->track_stability = true;
        if (T->root_infoset < 0) { printf("err no root infoset\n"); return; }
        Clock::time_point start = Clock::now();
        long before = T->iterations;
        do { iterate(*T); } while (ms_since(start) < ms);
        printf("ok iters=%ld pmax=%.6f value=%.6f\n", T->iterations - before, T->pmax, tree_value(*T));
    } else if (what == "result") {
        if (T->root_infoset < 0) { printf("err no root infoset\n"); return; }
        const Infoset& is = T->isets[T->root_infoset];
        size_t roots = 0, carried = 0, kluss = 0;
        for (const Node& n : T->nodes) if (n.parent < 0) { ++roots; if (!T->fresh_J[n.root_J]) { if (is_root_view_node(*T, n)) ++carried; else ++kluss; } }
        int max_depth = 0; double leaf_depth = 0; size_t leaves = 0;
        for (const Node& n : T->nodes) { max_depth = std::max(max_depth, (int)n.depth); if (!(n.flags & EXPANDED)) { leaf_depth += n.depth; ++leaves; } }
        printf("result %d pmax=%.6f value=%.6f nodes=%zu infosets=%zu iters=%ld roots=%zu carried=%zu kluss=%zu depth=%d leaf_depth=%.2f\n",
               (int)is.n, T->pmax, tree_value(*T), T->nodes.size(), T->isets.size(), T->iterations, roots, carried, kluss,
               max_depth, leaves ? leaf_depth / (double)leaves : 0.0);
        for (int k = 0; k < is.n; ++k) {
            size_t sl = is.start + k;
            int stable = T->stable.size() == is.n ? T->stable[k] : 1;
            printf("a %s %.9g %.9g %d\n", to_uci(T->sides[OURS].slot_move[sl]).c_str(), T->sides[OURS].strategy[sl], T->sides[OURS].u[sl], stable);
        }
    } else {
        printf("err unknown tree command\n");
    }
}

int main(int argc, char** argv) {
    init_tables();
    signal(SIGPIPE, SIG_IGN);  // a dead engine must not take the helper with it
    if (argc > 1 && !strcmp(argv[1], "selftest")) return selftest();
    std::ios::sync_with_stdio(false);
    S.states.resize(1);
    start_position(S.states[0]);
    S.weights.assign(1, 1.0);
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string command;
        in >> command;
        if (command == "quit") { engines::shutdown(); break; }
        if (command == "new") {
            std::string side;
            unsigned long long cap = 0, seed = 0;
            double head = 0.75;
            in >> side >> cap >> seed >> head;
            S = Set();
            S.side = side == "b" ? BLACK : WHITE;
            S.cap = std::max<size_t>((size_t)cap, 1);
            S.head_share = head > 0 && head <= 1 ? head : 0.75;
            S.rng.seed(seed);
            S.states.resize(1);
            start_position(S.states[0]);
            S.weights.assign(1, 1.0);
            report("ok", 1, 0, 0);
        } else if (command == "init" || command == "own" || command == "opp") {
            std::string move_text, view_text;
            double budget = 0;
            unsigned long long top = 0;
            Move move = 0;
            if (command == "own") in >> move_text;
            in >> view_text;
            if (command == "opp") in >> budget >> top;
            View view = parse_view(view_text);
            if (!view.ok || (command == "own" && !parse_uci(move_text, move))) { printf("err bad %s\n", command.c_str()); fflush(stdout); continue; }
            if (command == "init") {  // the first observation: the states as they stand
                std::vector<Pos> states;
                std::vector<double> weights;
                for (size_t i = 0; i < S.states.size(); ++i)
                    if (same_pieces(S.states[i], view) && !wins(S.states[i]) && visible_to(S.states[i], S.side) == view.visible) {
                        states.push_back(S.states[i]);
                        weights.push_back(1.0);
                    }
                size_t before = S.states.size();
                S.expanded = before;
                S.ms = 0;
                if (states.empty()) report("ok", 0, before, 0);  // nothing fits: the set stays as it was
                else {
                    S.states.swap(states);
                    S.weights.swap(weights);
                    report("ok", S.states.size(), before, S.states.size());
                }
            } else if (command == "own") {
                expand(view, true, move, 0);
                finish_own();
            } else {
                expand(view, false, 0, budget);
                S.pending = true;
                // The heaviest states that have a successor, for the policy to judge; not
                // the ones that could have taken our king, which are dealt with here.
                std::vector<uint32_t> listed;
                size_t with_kids = 0;
                for (size_t parent = 0; parent < S.flags.size(); ++parent)
                    if (S.flags[parent] & 1) { ++with_kids; if (!(S.flags[parent] & 2)) listed.push_back((uint32_t)parent); }
                std::stable_sort(listed.begin(), listed.end(), [](uint32_t a, uint32_t b) { return S.weights[a] > S.weights[b]; });
                if (listed.size() > top) listed.resize((size_t)top);
                printf("parents %zu %zu\n", with_kids, listed.size());
                for (uint32_t parent : listed) printf("p %u %u %s\n", parent, S.n_moves[parent], to_fen(S.states[parent], S.fullmove).c_str());
            }
        } else if (command == "commit") {
            int policy = 0;
            double king_miss = 0;
            unsigned long long count = 0;
            in >> policy >> king_miss >> count;
            std::vector<Table> tables;
            std::vector<int32_t> table_of(S.states.size(), -1);
            bool good = S.pending;
            for (unsigned long long i = 0; i < count; ++i) {
                std::string row_text, tag, uci;
                if (!std::getline(std::cin, row_text)) { good = false; break; }
                std::istringstream row(row_text);
                unsigned long long parent = 0, entries = 0;
                Table table;
                if (!(row >> tag >> parent >> table.other >> entries) || tag != "t" || parent >= table_of.size()) { good = false; continue; }
                for (unsigned long long j = 0; j < entries; ++j) {
                    double odds;
                    Move move;
                    if (!(row >> uci >> odds) || !parse_uci(uci, move)) { good = false; break; }
                    table.odds.push_back({move, odds});
                }
                table_of[(size_t)parent] = (int32_t)tables.size();
                tables.push_back(table);
            }
            if (!good) { S.pending = false; printf("err bad commit\n"); }
            else finish_opponent(policy != 0, king_miss, table_of, tables);
        } else if (command == "limit") {
            unsigned long long cap = 0;
            in >> cap;
            S.cap = std::max<size_t>((size_t)cap, 1);
            S.expanded = 0;
            S.ms = 0;
            if (S.states.size() > S.cap) { S.exact = false; cut(S.cap); }
            report("ok", S.states.size(), S.states.size(), S.states.size());
        } else if (command == "sample" || command == "dump" || command == "usample") {
            // usample: `count` distinct states drawn with equal odds whatever their weights,
            // so that a check over them can catch a truth the weights rate unlikely
            unsigned long long count = 0;
            in >> count;
            std::vector<std::pair<uint32_t, double>> chosen;
            if (command == "sample") sample((size_t)count, chosen);
            else if (command == "usample") {
                std::vector<uint32_t> order(S.states.size());
                std::iota(order.begin(), order.end(), 0u);
                for (size_t i = order.size(); i > 1; --i) std::swap(order[i - 1], order[S.rng.below(i)]);
                for (size_t i = 0; i < std::min<size_t>((size_t)count, order.size()); ++i) chosen.push_back({order[i], 1.0});
            }
            else for (size_t i = 0; i < std::min<size_t>((size_t)count, S.states.size()); ++i) chosen.push_back({(uint32_t)i, S.weights[i]});
            printf("%s %zu\n", command.c_str(), chosen.size());
            for (const auto& entry : chosen) printf("s %.17g %s\n", entry.second, to_fen(S.states[entry.first], S.fullmove).c_str());
        } else if (command == "load") {
            int exact = 0, weighted = 0;
            unsigned long long count = 0;
            in >> exact >> weighted >> count;
            std::vector<Pos> states;
            std::vector<double> weights;
            unsigned fullmove = S.fullmove;
            if (!read_states(std::cin, (size_t)count, states, weights, fullmove) || states.empty()) { printf("err bad load\n"); fflush(stdout); continue; }
            S.states.swap(states);
            S.weights.swap(weights);
            S.fullmove = fullmove;
            S.exact = exact != 0;
            S.weighted = weighted != 0;
            S.pending = false;
            S.expanded = 0;
            S.ms = 0;
            if (S.states.size() > S.cap) { S.exact = false; cut(S.cap); }
            report("ok", S.states.size(), S.states.size(), S.states.size());
        } else if (command == "find" || command == "moves" || command == "wins" || command == "obs" || command == "push") {
            std::string board, turn, castling, ep, half, full, extra;
            in >> board >> turn >> castling >> ep >> half >> full >> extra;
            Pos p;
            unsigned fullmove = 1;
            if (!parse_fen(board + " " + turn + " " + castling + " " + ep + " " + half + " " + full, p, fullmove)) { printf("err bad fen\n"); fflush(stdout); continue; }
            Move moves[MAX_MOVES];
            if (command == "find") {
                double total = 0, found = -1;
                for (size_t i = 0; i < S.states.size(); ++i) {
                    total += S.weights[i];
                    if (found < 0 && same_state(S.states[i], p)) found = S.weights[i];
                }
                if (found < 0) printf("missing %.17g\n", total);
                else printf("found %.17g %.17g\n", found, total);
            } else if (command == "moves") {
                int n = gen_moves(p, moves);
                printf("moves %d", n);
                for (int i = 0; i < n; ++i) printf(" %s", to_uci(moves[i]).c_str());
                printf("\n");
            } else if (command == "wins") {
                printf("wins %d\n", wins(p) ? 1 : 0);
            } else if (command == "obs") {
                printf("obs %s\n", observation(p, extra == "b" ? BLACK : WHITE).c_str());
            } else {
                Move move = 0;
                int n = gen_moves(p, moves);
                bool known = parse_uci(extra, move) && std::find(moves, moves + n, move) != moves + n;
                if (!known) printf("err not a move\n");
                else {
                    int mover = p.turn;
                    make(p, move);
                    printf("fen %s\n", to_fen(p, fullmove + (mover == BLACK ? 1 : 0)).c_str());
                }
            }
        } else if (command == "tree") {
            tree_command(in);
        } else {
            printf("err unknown command\n");
        }
        fflush(stdout);
    }
    return 0;
}
