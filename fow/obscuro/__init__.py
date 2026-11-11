"""A reduced Obscuro: belief tracking, a depth-2 imperfect-information subgame, PCFR+.

Section numbers in docstrings refer to "Obscuro: the search pipeline, formally".

    belief      the set P of positions consistent with our observations   (section 2)
    rules       terminal checks shared by the belief and the subgame
    evaluation  heuristic leaf value in [-1, 1]                            (section 8.1)
    subgame     the depth-2 game as flat arrays                            (section 8.1)
    regret      predictive regret matching+ over many infosets             (section 4.2)
    solver      alternating PCFR+ on the depth-2 game                      (section 4)
    search      time budget, root sampling, move choice                    (sections 6, 7)
"""
