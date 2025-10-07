# L.csv
punta_l = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21, 22, 23]
medio_l =  [11, 12, 14, 15]
talón_l = [13, 24, 25, 26, 27, 28, 29, 30, 31]

# R.csv
punta_r = [4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31]
medio_r = [0, 1, 3, 6]
talón_r = [2, 16, 17, 18, 19, 20, 21, 22, 23]


print(len(punta_l) + len(medio_l) + len(talón_l))
print(len(punta_r) + len(medio_r) + len(talón_r))
print(len(punta_l) + len(medio_l) + len(talón_l) == 32)
print(len(punta_r) + len(medio_r) + len(talón_r) == 32)

print(len(punta_l) == len(punta_r))
print(len(medio_l) == len(medio_r))
print(len(talón_l) == len(talón_r))

for i in range(32):
    if i not in punta_l and i not in medio_l and i not in talón_l:
        print(f"Falta {i} en el pie izquierdo")
    if i not in punta_r and i not in medio_r and i not in talón_r:
        print(f"Falta {i} en el pie derecho")


print(sorted(punta_l))
print(sorted(medio_l))
print(sorted(talón_l))
print(sorted(punta_r))
print(sorted(medio_r))
print(sorted(talón_r))