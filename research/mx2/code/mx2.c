// MX2 kernel: v1-overlay rules (AND/OR of 1-4 atoms) x 4 actions, yearly log-growth difference vs v1,
// walk-forward top-K per cutoff year by two scores (t over training years, total sum). <=2014 data only.
// build: gcc -O3 -march=native -fopenmp -o mx2 mx2.c -lm
// run:   ./mx2 <in.bin> <out.bin> <mode> <N> <seed>   mode: 0 = exhaustive sizes 1-3, 1 = random size-4, 2 = random subset sizes 2-4
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#define NH 120
#define NY 60
#define C0 11          // first cutoff (test year index 11 = 1966)
#define NC (NY - C0)   // 49 cutoffs
#define K 64
#define NACT 4
#define MINACT 4
static int nA; static uint8_t *A; static float *T;   // T[act][h][128]
typedef struct { double s[NC][2][K]; uint64_t code[NC][2][K]; double mn[NC][2]; int mi[NC][2]; uint64_t n_eval; } Heap;
static Heap *H;
static inline uint64_t sm64(uint64_t *x) { uint64_t z = (*x += 0x9E3779B97F4A7C15ULL); z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL; z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL; return z ^ (z >> 31); }
static inline void hins(Heap *h, int c, int st, double sc, uint64_t code) {
    if (sc <= h->mn[c][st]) return;
    int act = (int)(code >> 62);
    for (int k = 0; k < K; k++) if (h->s[c][st][k] == sc && (int)(h->code[c][st][k] >> 62) == act) return;  // duplicate pattern
    int m = h->mi[c][st]; h->s[c][st][m] = sc; h->code[c][st][m] = code;
    double mv = h->s[c][st][0]; int mi = 0;
    for (int k = 1; k < K; k++) if (h->s[c][st][k] < mv) { mv = h->s[c][st][k]; mi = k; }
    h->mn[c][st] = mv; h->mi[c][st] = mi;
}
static inline void evalv(Heap *h, const uint8_t *v, uint64_t code) {
    uint8_t idx[NH];
    idx[0] = v[0];
    for (int i = 1; i < NH; i++) idx[i] = v[i] | (((v[i - 1] >> 5) & 1) << 6);
    for (int a = 0; a < NACT; a++) {
        const float *Ta = T + (size_t)a * NH * 128;
        double cum = 0, cs = 0; int na = 0; double S[NY];
        for (int y = 0; y < NY; y++) S[y] = (double)Ta[(2 * y) * 128 + idx[2 * y]] + (double)Ta[(2 * y + 1) * 128 + idx[2 * y + 1]];
        for (int y = 0; y < C0; y++) { cum += S[y]; cs += S[y] * S[y]; na += (S[y] != 0); }
        uint64_t cd = code | ((uint64_t)a << 62);
        for (int c = 0; c < NC; c++) {
            int n = C0 + c;  // training years 0..n-1
            if (na >= MINACT && cum > 0) {
                double var = (cs - cum * cum / n) / (n - 1);
                double t = var > 0 ? cum / sqrt(n * var) : 0;
                hins(h, c, 0, t, cd);
                hins(h, c, 1, cum, cd);
            }
            double s = S[n]; cum += s; cs += s * s; na += (s != 0);
        }
        h->n_eval++;
    }
}
static inline void comb(uint8_t *v, int shape, const uint8_t *a, const uint8_t *b, const uint8_t *c, const uint8_t *d) {
    for (int i = 0; i < NH; i++) {
        uint8_t x;
        switch (shape) {
            case 0: x = a[i]; break;
            case 1: x = a[i] & b[i]; break;
            case 2: x = a[i] | b[i]; break;
            case 3: x = a[i] & b[i] & c[i]; break;
            case 4: x = a[i] & (b[i] | c[i]); break;
            case 5: x = b[i] & (a[i] | c[i]); break;
            case 6: x = c[i] & (a[i] | b[i]); break;
            case 7: x = a[i] | (b[i] & c[i]); break;
            case 8: x = b[i] | (a[i] & c[i]); break;
            case 9: x = c[i] | (a[i] & b[i]); break;
            case 10: x = a[i] | b[i] | c[i]; break;
            case 11: x = a[i] & b[i] & c[i] & d[i]; break;
            case 12: x = (a[i] & b[i]) | (c[i] & d[i]); break;
            case 13: x = a[i] & b[i] & (c[i] | d[i]); break;
            case 14: x = a[i] & (b[i] | c[i] | d[i]); break;
            case 15: x = a[i] | b[i] | c[i] | d[i]; break;
            default: x = (a[i] | b[i]) & (c[i] | d[i]); break;
        }
        v[i] = x;
    }
}
#define AT(i) (A + (size_t)(i) * 128)
static inline uint64_t enc(int shape, int a, int b, int c, int d) { return (uint64_t)shape | ((uint64_t)a << 5) | ((uint64_t)b << 16) | ((uint64_t)c << 27) | ((uint64_t)d << 38); }
int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage\n"); return 1; }
    FILE *f = fopen(argv[1], "rb"); int32_t hdr[1]; fread(hdr, 4, 1, f); nA = hdr[0];
    A = aligned_alloc(64, (size_t)nA * 128); fread(A, 1, (size_t)nA * 128, f);
    T = malloc(sizeof(float) * NACT * NH * 128); fread(T, sizeof(float), NACT * NH * 128, f); fclose(f);
    int mode = atoi(argv[3]); long long N = atoll(argv[4]); uint64_t seed = strtoull(argv[5], 0, 10);
    int nt = omp_get_max_threads(); H = calloc(nt, sizeof(Heap));
    for (int t = 0; t < nt; t++) for (int c = 0; c < NC; c++) for (int s = 0; s < 2; s++) { H[t].mn[c][s] = -1e300; for (int k = 0; k < K; k++) H[t].s[c][s][k] = -1e300; }
    double t0 = omp_get_wtime();
    if (mode == 0) {
        #pragma omp parallel
        {
            Heap *h = &H[omp_get_thread_num()]; uint8_t v[NH];
            #pragma omp for schedule(dynamic, 1)
            for (int a = 0; a < nA; a++) {
                evalv(h, AT(a), enc(0, a, 0, 0, 0));
                for (int b = a + 1; b < nA; b++) {
                    comb(v, 1, AT(a), AT(b), 0, 0); evalv(h, v, enc(1, a, b, 0, 0));
                    comb(v, 2, AT(a), AT(b), 0, 0); evalv(h, v, enc(2, a, b, 0, 0));
                    for (int c = b + 1; c < nA; c++)
                        for (int s = 3; s <= 10; s++) { comb(v, s, AT(a), AT(b), AT(c), 0); evalv(h, v, enc(s, a, b, c, 0)); }
                }
            }
        }
    } else {
        #pragma omp parallel
        {
            int tid = omp_get_thread_num(); Heap *h = &H[tid]; uint8_t v[NH];
            uint64_t st = seed * 1000003ULL + (uint64_t)tid * 7919ULL + 17;
            long long per = (N + nt - 1) / nt;
            for (long long i = 0; i < per; i++) {
                int sz, shape; uint64_t r = sm64(&st);
                if (mode == 1) sz = 4; else { int u = (int)(r % 10); sz = u < 1 ? 2 : (u < 5 ? 3 : 4); }
                int a = (int)(sm64(&st) % nA), b = (int)(sm64(&st) % nA), c = (int)(sm64(&st) % nA), d = (int)(sm64(&st) % nA);
                if (sz == 2) { if (a == b) continue; shape = 1 + (int)((r >> 8) % 2); }
                else if (sz == 3) { if (a == b || a == c || b == c) continue; shape = 3 + (int)((r >> 8) % 8); }
                else { if (a == b || a == c || a == d || b == c || b == d || c == d) continue; shape = 11 + (int)((r >> 8) % 6); }
                comb(v, shape, AT(a), AT(b), AT(c), AT(d)); evalv(h, v, enc(shape, a, b, c, d));
            }
        }
    }
    uint64_t ne = 0; for (int t = 0; t < nt; t++) ne += H[t].n_eval;
    FILE *o = fopen(argv[2], "wb"); int32_t meta[4] = {nt, NC, K, 2}; fwrite(meta, 4, 4, o); fwrite(&ne, 8, 1, o);
    for (int t = 0; t < nt; t++) for (int c = 0; c < NC; c++) for (int s = 0; s < 2; s++) { fwrite(H[t].s[c][s], 8, K, o); fwrite(H[t].code[c][s], 8, K, o); }
    fclose(o);
    fprintf(stderr, "mode %d evals %llu time %.1fs\n", mode, (unsigned long long)ne, omp_get_wtime() - t0);
    return 0;
}
