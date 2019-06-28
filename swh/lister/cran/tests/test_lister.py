from unittest.mock import patch
from swh.lister.cran.lister import CRANLister


def test_task_dict():
    lister = CRANLister()
    lister.descriptions['test_pack'] = 'Test Description'
    with patch('swh.lister.cran.lister.create_task_dict') as mock_create_tasks:
        lister.task_dict(origin_type='cran', origin_url='https://abc',
                         name='test_pack')
    mock_create_tasks.assert_called_once_with(
        'load-cran', 'recurring', 'test_pack', 'https://abc', None,
        project_metadata='Test Description')
