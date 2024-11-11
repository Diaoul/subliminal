# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/Diaoul/subliminal/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                      |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| subliminal/converters/addic7ed.py         |       26 |        4 |       12 |        4 |     79% |51, 53, 62, 64 |
| subliminal/converters/opensubtitles.py    |       29 |        1 |        6 |        1 |     94% |        64 |
| subliminal/converters/opensubtitlescom.py |       20 |        1 |        6 |        1 |     92% |        42 |
| subliminal/converters/tvsubtitles.py      |       19 |        1 |        6 |        1 |     92% |        34 |
| subliminal/core.py                        |      317 |       25 |      124 |        8 |     91% |171-172, 177-179, 197-198, 257-258, 273->298, 285->289, 339, 351-353, 702-714 |
| subliminal/providers/\_\_init\_\_.py      |       79 |        2 |       12 |        1 |     97% |67->exit, 151, 273 |
| subliminal/providers/addic7ed.py          |      302 |      103 |       92 |       20 |     61% |167-177, 198->201, 252-258, 263, 279, 288-289, 311-339, 343-357, 376-406, 410-420, 430, 437->441, 467-468, 479-489, 498->504, 500->498, 525, 528, 544-545, 557-558, 595, 602-603, 613, 626-627, 631 |
| subliminal/providers/bsplayer.py          |      175 |       31 |       42 |       10 |     76% |71, 74, 86-88, 95, 99-101, 154-158, 163-167, 172-176, 265->267, 279-280, 286, 290-291, 302, 317, 321->347 |
| subliminal/providers/gestdown.py          |      184 |       31 |       56 |       16 |     79% |113-119, 140->147, 174, 188, 227->233, 229->227, 246, 252-254, 260-261, 283, 299-300, 329-330, 379, 386-387, 399, 402, 409-411, 416-417, 421 |
| subliminal/providers/napiprojekt.py       |       92 |        8 |       14 |        3 |     90% |72, 123, 133-138, 156 |
| subliminal/providers/opensubtitles.py     |      216 |       20 |       66 |       12 |     86% |103-107, 115, 123, 148-149, 159-162, 249, 327, 414, 416, 418, 420, 422, 424 |
| subliminal/providers/opensubtitlescom.py  |      407 |       58 |      142 |       39 |     81% |139, 303-307, 338, 357-358, 417, 425, 431-432, 440-441, 446, 448-449, 469-470, 483, 490-491, 503, 510, 517, 525, 542, 550-554, 567, 581, 600, 627, 630-632, 635, 643, 655, 659, 662->674, 717->720, 720->723, 733->736, 751, 758, 765-769, 777-778, 850, 852, 854, 856, 858, 860 |
| subliminal/providers/podnapisi.py         |      127 |       14 |       30 |        9 |     85% |64, 111, 136, 167-168, 171-172, 204-205, 219, 230, 235, 249-250 |
| subliminal/providers/subtitulamos.py      |      139 |        3 |       32 |        2 |     97% |157-158, 255 |
| subliminal/providers/tvsubtitles.py       |      166 |       15 |       46 |       14 |     86% |74, 90->92, 92->95, 148, 163, 176-177, 201, 237, 279, 285->291, 298-299, 304, 312->327, 319-320, 329-330 |
| subliminal/refiners/hash.py               |       48 |       18 |       18 |        0 |     55% |    77-104 |
| subliminal/refiners/metadata.py           |       68 |       28 |       34 |       12 |     55% |36, 41-42, 53-57, 63-70, 77-78, 80-81, 82->89, 86, 90->115, 96-101, 103-107, 113 |
| subliminal/refiners/omdb.py               |      167 |       34 |       62 |       17 |     76% |29-31, 73-84, 97-98, 125-126, 128, 178, 187->184, 201, 211-212, 217-218, 222->229, 225-226, 252-253, 258-259, 266-267, 275->270, 279-280, 311, 318->321 |
| subliminal/refiners/tmdb.py               |      164 |       27 |       48 |       12 |     80% |25-27, 126, 132, 137, 181, 193-197, 209-213, 227->exit, 235-236, 242-243, 263, 280-281, 286-287, 295, 336->339 |
| subliminal/refiners/tvdb.py               |      225 |       27 |       62 |       15 |     85% |39, 182, 184, 256, 273-279, 295, 311, 325, 329, 359-360, 364-365, 369, 375-376, 449-450, 452-453, 473-474 |
| subliminal/score.py                       |       57 |       11 |       24 |        5 |     80% |137, 179-180, 182-183, 185-186, 188-189, 192-193 |
| subliminal/subtitle.py                    |      214 |        0 |       58 |        1 |     99% |  453->456 |
|                                 **TOTAL** | **3691** |  **462** | **1094** |  **203** | **84%** |           |

10 files skipped due to complete coverage.


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