import jntajis

candidates = [jntajis.jnta_shrink_translit(c) for c in jntajis.mj_shrink_candidates("器", 0b1111)]
print(ord(candidates[0]), ord(candidates[1]), candidates[0] == candidates[1])
