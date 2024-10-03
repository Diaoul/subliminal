# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| subliminal/converters/opensubtitlescom.py |       20 |        1 |        6 |        1 |     92% |        40 |
| subliminal/core.py                        |      313 |       28 |      134 |        8 |     91% |143-144, 150-153, 171-172, 177-179, 197-198, 261->286, 273->277, 327, 339-341, 690-702 |
| subliminal/providers/\_\_init\_\_.py      |       79 |        2 |       20 |        1 |     97% |67->exit, 151, 273 |
| subliminal/providers/addic7ed.py          |      302 |      103 |      102 |       20 |     62% |167-177, 198->201, 252-258, 263, 279, 288-289, 311-339, 343-357, 376-406, 410-420, 430, 437->441, 467-468, 479-489, 498->504, 500->498, 525, 528, 544-545, 557-558, 595, 602-603, 613, 626-627, 631 |
| subliminal/providers/bsplayer.py          |      175 |       37 |       55 |        9 |     74% |71, 74, 86-88, 95, 99-101, 154-158, 163-167, 172-176, 263-269, 279-280, 286, 290-291, 302, 317, 321->347 |
| subliminal/providers/gestdown.py          |      184 |       31 |       59 |       16 |     79% |113-119, 140->147, 174, 188, 227->233, 229->227, 246, 252-254, 260-261, 283, 299-300, 329-330, 379, 386-387, 399, 402, 409-411, 416-417, 421 |
| subliminal/providers/napiprojekt.py       |       92 |        8 |       22 |        3 |     89% |72, 123, 133-138, 156 |
| subliminal/providers/opensubtitles.py     |      211 |       20 |       74 |       12 |     86% |93-97, 105, 113, 138-139, 149-152, 239, 317, 404, 406, 408, 410, 412, 414 |
| subliminal/providers/opensubtitlescom.py  |      406 |       58 |      167 |       39 |     81% |139, 293-297, 328, 347-348, 407, 415, 421-422, 430-431, 436, 438-439, 459-460, 473, 480-481, 493, 500, 507, 515, 532, 540-544, 557, 571, 590, 617, 620-622, 625, 633, 645, 649, 652->664, 706->709, 709->712, 722->725, 740, 747, 754-758, 766-767, 839, 841, 843, 845, 847, 849 |
| subliminal/providers/podnapisi.py         |      127 |       14 |       34 |        9 |     86% |64, 111, 136, 167-168, 171-172, 204-205, 219, 230, 235, 249-250 |
| subliminal/providers/tvsubtitles.py       |      166 |       15 |       58 |       14 |     87% |74, 90->92, 92->95, 148, 163, 176-177, 201, 237, 279, 285->291, 298-299, 304, 312->327, 319-320, 329-330 |
| subliminal/refiners/hash.py               |       47 |       17 |       21 |        0 |     57% |    77-102 |
| subliminal/refiners/metadata.py           |       68 |       28 |       36 |       12 |     56% |36, 41-42, 53-57, 63-70, 77-78, 80-81, 82->89, 86, 90->115, 96-101, 103-107, 113 |
| subliminal/refiners/omdb.py               |      167 |       34 |       74 |       17 |     77% |29-31, 73-84, 97-98, 125-126, 128, 178, 187->184, 201, 211-212, 217-218, 222->229, 225-226, 252-253, 258-259, 266-267, 275->270, 279-280, 311, 318->321 |
| subliminal/refiners/tmdb.py               |      164 |       27 |       64 |       12 |     81% |25-27, 126, 132, 137, 181, 193-197, 209-213, 227->exit, 235-236, 242-243, 263, 280-281, 286-287, 295, 336->339 |
| subliminal/refiners/tvdb.py               |      225 |       27 |      116 |       15 |     87% |39, 182, 184, 256, 273-279, 295, 311, 325, 329, 359-360, 364-365, 369, 375-376, 449-450, 452-453, 473-474 |
| subliminal/score.py                       |       60 |       10 |       28 |        5 |     83% |180-181, 183-184, 186-187, 189-190, 193-194 |
| subliminal/subtitle.py                    |      214 |        0 |       76 |        1 |     99% |  451->454 |
|                                 **TOTAL** | **3490** |  **460** | **1292** |  **194** | **84%** |           |

11 files skipped due to complete coverage.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/Diaoul/subliminal/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Diaoul/subliminal/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2FDiaoul%2Fsubliminal%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.