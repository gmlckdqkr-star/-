import sys, hashlib; sys.path.insert(0, sys.argv[1])
import xv1, t_world, m_batch1
t_world.old(); C = m_batch1.configs()
print(len(C), hashlib.sha256(''.join(c.hash for c in C).encode()).hexdigest()[:16], hashlib.sha256(''.join(sorted(c.hash for c in C)).encode()).hexdigest()[:16])
print('gate', sorted(set((f.split('/')[-1], bool(xv1.gate(f))) for f in set(c.file for c in C))))
