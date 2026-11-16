/* Grid maze router core for tools/v5/route/router.py (built with gcc -O2 -shared -fPIC).
 *
 * State = (layer, cell, direction of arrival). 8 directions + "none" (start / after a via).
 * Cost: 100 per orthogonal step, 141 per diagonal step, each times the layer factor lmul[l]/100,
 * plus the per-cell extra cost, plus a penalty per 45 degree turn (90 = two; sharper turns are not
 * allowed), plus viacost per layer change. blk[l][cell] != 0: no track centre here on layer l.
 * vok[cell] != 0: a via may sit here. tgt[l][cell] != 0: target.
 * Returns the number of path points written (layer, x, y triples, target first), 0 if no path,
 * -1 if out of memory / the output buffer is too small.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t f; uint32_t s; } HN;
typedef struct { HN *a; size_t n, cap; } Heap;

static int hpush(Heap *h, uint32_t f, uint32_t s) {
    if (h->n == h->cap) {
        size_t nc = h->cap ? h->cap * 2 : 1 << 16;
        HN *na = realloc(h->a, nc * sizeof(HN));
        if (!na) return -1;
        h->a = na; h->cap = nc;
    }
    size_t i = h->n++;
    while (i) {
        size_t p = (i - 1) >> 1;
        if (h->a[p].f <= f) break;
        h->a[i] = h->a[p]; i = p;
    }
    h->a[i].f = f; h->a[i].s = s;
    return 0;
}

static HN hpop(Heap *h) {
    HN top = h->a[0], last = h->a[--h->n];
    size_t i = 0;
    for (;;) {
        size_t c = 2 * i + 1;
        if (c >= h->n) break;
        if (c + 1 < h->n && h->a[c + 1].f < h->a[c].f) c++;
        if (h->a[c].f >= last.f) break;
        h->a[i] = h->a[c]; i = c;
    }
    h->a[i] = last;
    return top;
}

static const int DX[8] = {1, 1, 0, -1, -1, -1, 0, 1};
static const int DY[8] = {0, 1, 1, 1, 0, -1, -1, -1};

int route(int W, int H, int NL, const uint8_t *blk, const uint8_t *xcost, const uint8_t *vok, const uint8_t *tgt,
          const int32_t *src, int nsrc, const int32_t *lmul, int viacost, int turncost,
          int tx0, int ty0, int tx1, int ty1, int32_t *out, int maxout, int64_t *expanded) {
    size_t ncell = (size_t)W * H, nstate = ncell * NL * 9;
    uint32_t *g = malloc(nstate * sizeof(uint32_t));
    uint8_t *par = malloc(nstate);
    if (!g || !par) { free(g); free(par); return -1; }
    memset(g, 0xff, nstate * sizeof(uint32_t));
    Heap hp = {0, 0, 0};
    int minmul = 1000000;
    for (int l = 0; l < NL; l++) if (lmul[l] < minmul) minmul = lmul[l];
#define HEUR(x, y) ({ int dx_ = (x) < tx0 ? tx0 - (x) : ((x) > tx1 ? (x) - tx1 : 0); \
                      int dy_ = (y) < ty0 ? ty0 - (y) : ((y) > ty1 ? (y) - ty1 : 0); \
                      int mn_ = dx_ < dy_ ? dx_ : dy_, mx_ = dx_ < dy_ ? dy_ : dx_; \
                      (uint32_t)((mx_ * 100 + mn_ * 41) * (int64_t)minmul / 100); })
    for (int i = 0; i < nsrc; i++) {
        int l = src[3 * i], x = src[3 * i + 1], y = src[3 * i + 2];
        if (l < 0 || l >= NL || x < 0 || x >= W || y < 0 || y >= H) continue;
        size_t c = (size_t)y * W + x;
        if (blk[l * ncell + c]) continue;
        size_t s = (l * ncell + c) * 9 + 8;
        g[s] = 0; par[s] = 255;
        if (hpush(&hp, HEUR(x, y), (uint32_t)s)) goto oom;
    }
    int64_t nexp = 0;
    size_t goal = (size_t)-1;
    while (hp.n) {
        HN top = hpop(&hp);
        size_t s = top.s;
        int d = s % 9;
        size_t lc = s / 9;
        int l = lc / ncell;
        size_t c = lc % ncell;
        int x = c % W, y = c / W;
        uint32_t gs = g[s];
        if (top.f != gs + HEUR(x, y)) continue;
        nexp++;
        if (tgt[l * ncell + c]) { goal = s; break; }
        for (int nd = 0; nd < 8; nd++) {
            int turn = 0;
            if (d != 8) {
                int df = nd > d ? nd - d : d - nd;
                if (df > 4) df = 8 - df;
                if (df > 2) continue;
                turn = df * turncost;
            }
            int nx = x + DX[nd], ny = y + DY[nd];
            if (nx < 0 || nx >= W || ny < 0 || ny >= H) continue;
            size_t nc = (size_t)ny * W + nx;
            const uint8_t *bl = blk + l * ncell;
            if (bl[nc]) continue;
            if (nd & 1) { if (bl[(size_t)y * W + nx] || bl[(size_t)ny * W + x]) continue; }
            uint32_t step = (nd & 1) ? 141 : 100;
            uint32_t ng = gs + (step * (lmul[l] + xcost[l * ncell + nc])) / 100 + turn;
            size_t ns = (l * ncell + nc) * 9 + nd;
            if (ng < g[ns]) {
                g[ns] = ng; par[ns] = (uint8_t)d;
                if (hpush(&hp, ng + HEUR(nx, ny), (uint32_t)ns)) goto oom;
            }
        }
        if (vok[c] && par[s] < 16) {     /* no via right after a via */
            for (int nl = 0; nl < NL; nl++) {
                if (nl == l || blk[nl * ncell + c]) continue;
                uint32_t ng = gs + viacost;
                size_t ns = (nl * ncell + c) * 9 + 8;
                if (ng < g[ns]) {
                    g[ns] = ng; par[ns] = (uint8_t)(16 + l * 9 + d);
                    if (hpush(&hp, ng + HEUR(x, y), (uint32_t)ns)) goto oom;
                }
            }
        }
    }
    *expanded = nexp;
    int n = 0;
    if (goal != (size_t)-1) {
        size_t s = goal;
        for (;;) {
            int d = s % 9;
            size_t lc = s / 9;
            int l = lc / ncell;
            size_t c = lc % ncell;
            if (n >= maxout) { n = -1; break; }
            out[3 * n] = l; out[3 * n + 1] = c % W; out[3 * n + 2] = c / W; n++;
            uint8_t p = par[s];
            if (p == 255) break;
            if (p >= 16) { int pl = (p - 16) / 9, pd = (p - 16) % 9; s = (pl * ncell + c) * 9 + pd; }
            else { size_t pc = c - DX[d] - (size_t)DY[d] * W; s = (l * ncell + pc) * 9 + p; }
        }
    }
    free(g); free(par); free(hp.a);
    return n;
oom:
    free(g); free(par); free(hp.a);
    return -1;
}
