# Copyright (C) 2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def assert_sleep_calls(mocker, mock_sleep, sleep_params):
    mock_sleep.assert_has_calls([mocker.call(param) for param in sleep_params])
