# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------ | -------: | -------: | ------: | --------: |
| subliminal/converters/opensubtitlescom.py |       20 |        1 |     95% |        40 |
| subliminal/converters/shooter.py          |       19 |       19 |      0% |      3-37 |
| subliminal/converters/thesubdb.py         |       21 |       21 |      0% |      3-50 |
| subliminal/core.py                        |      328 |       31 |     91% |103-104, 133-134, 161-162, 167-169, 187-188, 194, 248-249, 318-320, 457-458, 491-501, 570-572, 625, 633-634 |
| subliminal/extensions.py                  |       60 |       11 |     82% |57-59, 71-72, 76-77, 99-100, 117-118 |
| subliminal/matches.py                     |       57 |        3 |     95% |70, 136, 145 |
| subliminal/providers/\_\_init\_\_.py      |       74 |        1 |     99% |       259 |
| subliminal/providers/addic7ed.py          |      302 |      103 |     66% |167-177, 252-258, 263, 279, 288-289, 311-339, 343-357, 376-406, 410-420, 430, 467-468, 479-489, 525, 528, 544-545, 557-558, 595, 602-603, 613, 626-627, 631 |
| subliminal/providers/gestdown.py          |      184 |       31 |     83% |113-119, 174, 188, 246, 252-254, 260-261, 283, 299-300, 329-330, 379, 386-387, 399, 402, 409-411, 416-417, 421 |
| subliminal/providers/napiprojekt.py       |       85 |        8 |     91% |70, 107, 117-122, 140 |
| subliminal/providers/opensubtitles.py     |      219 |       20 |     91% |108-112, 120, 128, 153-154, 164-167, 255, 333, 420, 422, 424, 426, 428, 430 |
| subliminal/providers/opensubtitlescom.py  |      406 |       58 |     86% |139, 293-297, 328, 347-348, 407, 415, 421-422, 430-431, 436, 438-439, 459-460, 473, 480-481, 493, 500, 507, 515, 532, 540-544, 557, 571, 590, 617, 620-622, 625, 633, 645, 649, 740, 747, 754-758, 766-767, 839, 841, 843, 845, 847, 849 |
| subliminal/providers/podnapisi.py         |      127 |       14 |     89% |64, 111, 136, 167-168, 171-172, 204-205, 219, 230, 235, 249-250 |
| subliminal/providers/tvsubtitles.py       |      166 |       15 |     91% |74, 148, 163, 176-177, 201, 237, 279, 298-299, 304, 319-320, 329-330 |
| subliminal/refiners/hash.py               |       74 |       19 |     74% |83-86, 97-107, 136-137, 146, 149 |
| subliminal/refiners/metadata.py           |       67 |       28 |     58% |34, 39-40, 51-55, 61-68, 75-76, 78-79, 84, 94-99, 101-105, 111 |
| subliminal/refiners/omdb.py               |      167 |       34 |     80% |29-31, 73-84, 97-98, 125-126, 128, 178, 201, 211-212, 217-218, 225-226, 252-253, 258-259, 266-267, 279-280, 311 |
| subliminal/refiners/tmdb.py               |      164 |       27 |     84% |25-27, 126, 132, 137, 181, 193-197, 209-213, 235-236, 242-243, 263, 280-281, 286-287, 295 |
| subliminal/refiners/tvdb.py               |      225 |       27 |     88% |39, 182, 184, 256, 273-279, 295, 311, 325, 329, 359-360, 364-365, 369, 375-376, 449-450, 452-453, 473-474 |
| subliminal/score.py                       |       84 |       18 |     79% |111-115, 150, 198-199, 201-202, 204-205, 207-208, 211-212, 226-227 |
| subliminal/subtitle.py                    |      193 |       29 |     85% |139, 199, 204-206, 249-251, 254, 257, 304, 307, 310, 313, 316, 340, 342, 345-354, 411, 436-437, 440 |
| subliminal/utils.py                       |       77 |        6 |     92% |132, 141, 155, 158, 160, 164 |
| subliminal/video.py                       |      127 |        3 |     98% |250, 383, 472 |
|                                 **TOTAL** | **3333** |  **527** | **84%** |           |

7 files skipped due to complete coverage.


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