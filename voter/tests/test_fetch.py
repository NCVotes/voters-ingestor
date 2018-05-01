from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from voter.models import FileTracker
from voter import utils


class VoterFetchUtilsTest(TestCase):

    def setUp(self):
        self.url = 'http://example.com/file.zip'
        self.base_path = 'foo'
        self.etag = 'a made-up etag value'
        self.label = 'ncvoter'

    def test_derive_target_folder(self):
        "creates a folder path given a base_path and a date"
        now = timezone.now()
        expected_result = '{}/{}'.format(self.base_path, now.strftime('%Y-%m-%dT%H:%M:%S:%s'))
        result = utils.derive_target_folder(self.base_path, now)
        self.assertEqual(result, expected_result)

    @mock.patch('voter.utils.requests.get')
    def test_get_etag_and_zip_stream(self, mock_get):
        "returns the URL response and its etag header"
        mock_response = mock_get.return_value
        mock_response.headers = {'etag': self.etag}
        result = utils.get_etag_and_zip_stream(self.url)
        self.assertEqual(result, (self.etag, mock_response))

    @mock.patch('voter.utils.os.makedirs')
    def test_write_stream(self, mock_mkdirs):
        "mock that we can write a response to a mock file"
        mock_open = mock.mock_open()
        rsp = mock.Mock()
        rsp.headers = {'content-length': 1}
        rsp.iter_content.return_value = ['some', 'content']
        filename = 'foo/bar.txt'
        with mock.patch('voter.utils.open', mock_open, create=True):
            result = utils.write_stream(rsp, filename)
        mock_open.assert_called_once_with(filename, 'wb')
        self.assertEqual(result, True)

    def test_write_stream_ioerror(self):
        "IOError returns False"
        rsp = mock.Mock()
        # filename at root of filesystem should not be writable, so will generate IOError
        filename = '/foo.txt'
        result = utils.write_stream(rsp, filename)
        self.assertEqual(result, False)

    @mock.patch('voter.utils.subprocess.call')
    @mock.patch('voter.utils.os.remove')
    def test_extract_and_remove_file(self, mock_remove, mock_unzip):
        mock_unzip.return_value = 0
        filename = 'foo/bar.zip'
        result = utils.extract_and_remove_file(filename)
        self.assertEqual(result, True)
        mock_unzip.assert_called_once_with(['unzip', filename, '-d', 'foo'])
        mock_remove.assert_called_once_with(filename)

    @mock.patch('voter.utils.os.remove')
    def test_extract_and_remove_file_ioerror(self, mock_remove):
        filename = 'foo/bar.zip'
        result = utils.extract_and_remove_file(filename)
        self.assertEqual(result, False)
        # unzip failed, so we shouldn't have tried to remove the file
        mock_remove.assert_not_called()

    # helpers for attempt_fetch_and_write_new_zip testing

    def make_mock_response(self, status_code=200):
        rsp = mock.Mock(status_code=status_code,
                        headers={'content-length': 1})
        rsp.iter_content.return_value = []
        return rsp

    def make_now_and_expected_result(self, fetch_status_code):
        now = timezone.now()
        target_filename = '{}/{}/{}'.format(
            self.base_path, now.strftime('%Y-%m-%dT%H:%M:%S:%s'), self.url.split('/')[-1])
        expected_result = (
            fetch_status_code,
            self.etag,
            now,
            target_filename,
        )
        return now, expected_result

    @mock.patch('voter.utils.datetime')
    @mock.patch('voter.utils.get_etag_and_zip_stream')
    def test_attempt_fetch_and_write_new_zip_file_exists_already(self, mock_get_etag, mock_datetime):
        mock_get_etag.return_value = (self.etag, self.make_mock_response())
        now, expected_result = self.make_now_and_expected_result(utils.FETCH_STATUS_CODES.CODE_NOTHING_TO_DO)
        mock_datetime.now.return_value = now
        # create a FileTracker with this etag value -> CODE_NOTHING_TO_DO
        FileTracker.objects.create(etag=self.etag, created=now)
        result = utils.attempt_fetch_and_write_new_zip(self.url, self.base_path)
        self.assertEqual(result, expected_result)

    @mock.patch('voter.utils.write_stream')
    @mock.patch('voter.utils.datetime')
    @mock.patch('voter.utils.get_etag_and_zip_stream')
    def test_attempt_fetch_and_write_new_zip(self, mock_get_etag, mock_datetime, mock_write_stream):
        mock_get_etag.return_value = (self.etag, self.make_mock_response())
        now, expected_result = self.make_now_and_expected_result(utils.FETCH_STATUS_CODES.CODE_OK)
        mock_datetime.now.return_value = now
        # write is successful -> CODE_OK
        mock_write_stream.return_value = True
        result = utils.attempt_fetch_and_write_new_zip(self.url, self.base_path)
        self.assertEqual(result, expected_result)

    @mock.patch('voter.utils.write_stream')
    @mock.patch('voter.utils.datetime')
    @mock.patch('voter.utils.get_etag_and_zip_stream')
    def test_attempt_fetch_and_write_new_zip_write_failure(self, mock_get_etag, mock_datetime, mock_write_stream):
        mock_get_etag.return_value = (self.etag, self.make_mock_response())
        now, expected_result = self.make_now_and_expected_result(utils.FETCH_STATUS_CODES.CODE_WRITE_FAILURE)
        mock_datetime.now.return_value = now
        # write failure -> CODE_WRITE_FAILURE
        mock_write_stream.return_value = False
        result = utils.attempt_fetch_and_write_new_zip(self.url, self.base_path)
        self.assertEqual(result, expected_result)

    @mock.patch('voter.utils.datetime')
    @mock.patch('voter.utils.get_etag_and_zip_stream')
    def test_attempt_fetch_and_write_new_zip_net_failure(self, mock_get_etag, mock_datetime):
        # status_code != 200 -> CODE_NET_FAILURE
        mock_get_etag.return_value = (self.etag, self.make_mock_response(status_code=500))
        now, expected_result = self.make_now_and_expected_result(utils.FETCH_STATUS_CODES.CODE_NET_FAILURE)
        mock_datetime.now.return_value = now
        result = utils.attempt_fetch_and_write_new_zip(self.url, self.base_path)
        self.assertEqual(result, expected_result)

    @mock.patch('voter.utils.os.listdir')
    @mock.patch('voter.utils.extract_and_remove_file')
    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip(self, mock_fetch, mock_extract, mock_listdir):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_OK, self.etag, timezone.now(), ''
        mock_extract.return_value = True
        mock_listdir.return_value = ['bar.txt', 'ignored.foo']
        result = utils.process_new_zip(self.url, self.base_path, self.label)
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_OK)
        # FileTracker for .txt file gets created ...
        self.assertTrue(FileTracker.objects.filter(filename='bar.txt').exists())
        # ... but we ignore files that don't have a .txt extension
        self.assertFalse(FileTracker.objects.filter(filename='ignored.foo').exists())

    @mock.patch('voter.utils.os.listdir')
    @mock.patch('voter.utils.extract_and_remove_file')
    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip_ncvhis(self, mock_fetch, mock_extract, mock_listdir):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_OK, self.etag, timezone.now(), ''
        mock_extract.return_value = True
        mock_listdir.return_value = ['bar.txt', 'ignored.foo']
        result = utils.process_new_zip(self.url, self.base_path, 'ncvhis')
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_OK)
        # FileTracker for .txt file gets created ...
        self.assertTrue(FileTracker.objects.filter(filename='bar.txt').exists())
        # ... but we ignore files that don't have a .txt extension
        self.assertFalse(FileTracker.objects.filter(filename='ignored.foo').exists())

    @mock.patch('voter.utils.extract_and_remove_file')
    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip_unable_to_unzip(self, mock_fetch, mock_extract):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_OK, None, None, None
        mock_extract.return_value = False
        result = utils.process_new_zip(self.url, self.base_path, self.label)
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_WRITE_FAILURE)

    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip_already_downloaded(self, mock_fetch):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_NOTHING_TO_DO, None, None, None
        result = utils.process_new_zip(self.url, self.base_path, self.label)
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_NOTHING_TO_DO)

    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip_net_failure(self, mock_fetch):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_NET_FAILURE, None, None, None
        result = utils.process_new_zip(self.url, self.base_path, self.label)
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_NET_FAILURE)

    @mock.patch('voter.utils.attempt_fetch_and_write_new_zip')
    def test_process_new_zip_write_failure(self, mock_fetch):
        mock_fetch.return_value = utils.FETCH_STATUS_CODES.CODE_WRITE_FAILURE, None, None, None
        result = utils.process_new_zip(self.url, self.base_path, self.label)
        self.assertEqual(result, utils.FETCH_STATUS_CODES.CODE_WRITE_FAILURE)


class VoterFetchHistoricalTest(TestCase):

    @mock.patch('voter.management.commands.voter_fetch_snapshot.process_new_zip')
    @mock.patch('voter.management.commands.voter_fetch_snapshot.s3client.list_objects')
    def test_handle(self, mock_s3_list, mock_process_new_zip):
        mock_s3_list.return_value = {'Contents': [{'Key': 'http://example.com/foo.zip'}]}
        call_command('voter_fetch_snapshot')
        expected_url = settings.NCVOTER_HISTORICAL_SNAPSHOT_URL + 'foo.zip'
        mock_process_new_zip.assert_called_once_with(expected_url, settings.NCVOTER_DOWNLOAD_PATH, 'ncvoter')

    @mock.patch('voter.management.commands.voter_fetch_snapshot.process_new_zip')
    @mock.patch('voter.management.commands.voter_fetch_snapshot.s3client.list_objects')
    def test_handle_multiple_files(self, mock_s3_list, mock_process_new_zip):
        mock_s3_list.return_value = {'Contents': [{'Key': 'http://example.com/foo.zip'},
                                                  {'Key': 'http://example.com/bar.zip'}]}
        call_command('voter_fetch_snapshot')
        # We re-order alphabetically by the filename, so bar.zip comes before foo.zip
        expected_url1 = settings.NCVOTER_HISTORICAL_SNAPSHOT_URL + 'bar.zip'
        expected_url2 = settings.NCVOTER_HISTORICAL_SNAPSHOT_URL + 'foo.zip'
        expected = [
            # mock records tuples of (args, kwargs), but we don't send kwargs in our commands
            ((expected_url1, settings.NCVOTER_DOWNLOAD_PATH, 'ncvoter'), {}),
            ((expected_url2, settings.NCVOTER_DOWNLOAD_PATH, 'ncvoter'), {}),
        ]
        self.assertEqual(mock_process_new_zip.call_args_list, expected)

    @mock.patch('voter.management.commands.voter_fetch_snapshot.process_new_zip')
    @mock.patch('voter.management.commands.voter_fetch_snapshot.s3client.list_objects')
    def test_handle_skip_non_zip_files(self, mock_s3_list, mock_process_new_zip):
        mock_s3_list.return_value = {'Contents': [{'Key': 'http://example.com/foo.txt'},
                                                  {'Key': 'http://example.com/bar.txt'}]}
        call_command('voter_fetch_snapshot')
        self.assertEqual(mock_process_new_zip.call_count, 0)


class VoterFetchCurrentTest(TestCase):

    @mock.patch('voter.management.commands.voter_fetch.process_new_zip')
    def test_handle(self, mock_process_new_zip):
        call_command('voter_fetch')
        expected_url1 = settings.NCVOTER_LATEST_STATEWIDE_URL
        expected_url2 = settings.NCVHIS_LATEST_STATEWIDE_URL
        expected = [
            # mock records tuples of (args, kwargs), but we don't send kwargs in our commands
            ((expected_url1, settings.NCVOTER_DOWNLOAD_PATH, 'ncvoter', None), {}),
            ((expected_url2, settings.NCVHIS_DOWNLOAD_PATH, 'ncvhis', None), {}),
        ]
        self.assertEqual(mock_process_new_zip.call_args_list, expected)

    @mock.patch('voter.management.commands.voter_fetch.process_new_zip')
    def test_handle_county(self, mock_process_new_zip):
        call_command('voter_fetch', '--bycounty')
        # we don't currently do in-depth testing: just check that we try to process 200 files
        #   100 counties x 2 files per county (ncvoter and ncvhis)
        self.assertEqual(mock_process_new_zip.call_count, 200)
