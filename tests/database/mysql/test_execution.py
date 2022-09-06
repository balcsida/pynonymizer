import pytest
import unittest
from unittest.mock import patch, Mock
from pynonymizer.database.exceptions import DependencyError
from pynonymizer.database.mysql.execution import MySqlDumpRunner, MySqlCmdRunner
import subprocess


@patch("shutil.which", Mock(return_value=None))
class NoExecutablesInPathTests(unittest.TestCase):
    def test_dump_runner_missing_mysqldump(self):
        with pytest.raises(DependencyError):
            MySqlDumpRunner("1.2.3.4", "user", "password", "name", db_port=None)

    def test_cmd_runner_missing_mysql(self):
        with pytest.raises(DependencyError):
            MySqlCmdRunner("1.2.3.4", "user", "password", "name", db_port=None)


@patch("subprocess.Popen")
@patch("subprocess.check_output")
@patch("shutil.which", Mock(return_value="fake/path/to/executable"))
class DumperTests(unittest.TestCase):
    def test_open_dumper__when_omitting_optional_args__should_not_pass_args(
        self, check_output, popen
    ):
        dump_runner = MySqlDumpRunner(
            db_host=None,
            db_user=None,
            db_pass=None,
            db_name="db_name",
            db_port=None,
            additional_opts="--quick --single-transaction",
        )

        open_result = dump_runner.open_dumper()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "mysqldump",
                "--quick",
                "--single-transaction",
                "db_name",
            ],
            stdout=subprocess.PIPE,
        )

    def test_open_dumper__when_using_additional_opts__should_pass_split_args_to_popen(
        self, check_output, popen
    ):
        dump_runner = MySqlDumpRunner(
            db_host="1.2.3.4",
            db_user="db_user",
            db_pass="db_password",
            db_name="db_name",
            db_port=None,
            additional_opts="--quick --single-transaction",
        )

        open_result = dump_runner.open_dumper()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "mysqldump",
                "--host",
                "1.2.3.4",
                "--user",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "db_name",
            ],
            stdout=subprocess.PIPE,
        )

    def test_open_dumper__when_port_is_not_passed__should_use_defaults(
        self, check_output, popen
    ):
        dump_runner = MySqlDumpRunner(
            db_host="1.2.3.4",
            db_user="db_user",
            db_pass="db_password",
            db_name="db_name",
            db_port=None,
        )
        open_result = dump_runner.open_dumper()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "mysqldump",
                "--host",
                "1.2.3.4",
                "--user",
                "db_user",
                "-pdb_password",
                "db_name",
            ],
            stdout=subprocess.PIPE,
        )

        # dumper should return the stdout of that process
        assert open_result == popen.return_value.stdout

    def test_open_dumper__when_port_is_passed__should_use_passed(
        self, check_output, popen
    ):
        dump_runner = MySqlDumpRunner(
            "1.2.3.4", "db_user", "db_password", "db_name", db_port="3307"
        )
        open_result = dump_runner.open_dumper()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "mysqldump",
                "--host",
                "1.2.3.4",
                "--port",
                "3307",
                "--user",
                "db_user",
                "-pdb_password",
                "db_name",
            ],
            stdout=subprocess.PIPE,
        )

        # dumper should return the stdout of that process
        assert open_result == popen.return_value.stdout


@patch("subprocess.Popen")
@patch("subprocess.check_output")
@patch("shutil.which", Mock(return_value="fake/path/to/executable"))
class CmdTests(unittest.TestCase):
    def test__batch_processor__when_omitted_optional_args__should_not_call_cli_with_args(
        self, check_output, popen
    ):
        cmd_runner = MySqlCmdRunner(
            db_user=None,
            db_pass=None,
            db_name="db_name",
            db_host=None,
            db_port=None,
            additional_opts="--quick --single-transaction",
        )
        open_result = cmd_runner.open_batch_processor()

        popen.assert_called_with(
            [
                "mysql",
                "--quick",
                "--single-transaction",
                "db_name",
            ],
            stdin=subprocess.PIPE,
        )

    def test_open_batch_processor(self, check_output, popen):
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        open_result = cmd_runner.open_batch_processor()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "db_name",
            ],
            stdin=subprocess.PIPE,
        )

        # dumper should return the stdin of that process
        assert open_result == popen.return_value.stdin

    def test__execute__when_omitted_optional_args__should_not_call_cli_with_args(
        self, check_output, popen
    ):
        cmd_runner = MySqlCmdRunner(
            db_user=None,
            db_pass=None,
            db_name="db_name",
            db_host=None,
            db_port=None,
            additional_opts="--quick --single-transaction",
        )
        execute_result = cmd_runner.execute("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "mysql",
                "--quick",
                "--single-transaction",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )

    def test_execute(self, check_output, popen):
        """
        execute should execute an arbitrary statement with valid args
        """
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        execute_result = cmd_runner.execute("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )

    def test_execute_list(self, check_output, popen):
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        execute_result = cmd_runner.execute(
            ["SELECT `column` from `table`;", "SELECT `column2` from `table2`;"]
        )

        check_output.assert_any_call(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )

        check_output.assert_any_call(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "--execute",
                "SELECT `column2` from `table2`;",
            ]
        )

    def test_db_execute(self, check_output, popen):
        """
        execute should execute an arbitrary statement with valid args
        """
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        execute_result = cmd_runner.db_execute("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "db_name",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )

    def test_db_execute_list(self, check_output, popen):
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        execute_result = cmd_runner.db_execute(
            ["SELECT `column` from `table`;", "SELECT `column2` from `table2`;"]
        )

        check_output.assert_any_call(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "db_name",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )
        check_output.assert_any_call(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "--quick",
                "--single-transaction",
                "db_name",
                "--execute",
                "SELECT `column2` from `table2`;",
            ]
        )

    def test_get_single_result(self, check_output, popen):
        """
        execute should execute an arbitrary statement and return the decoded, no-column result
        """
        cmd_runner = MySqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="3306",
            additional_opts="--quick --single-transaction",
        )
        single_result = cmd_runner.get_single_result("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "mysql",
                "-h",
                "1.2.3.4",
                "-P",
                "3306",
                "-u",
                "db_user",
                "-pdb_password",
                "-sN",
                "--quick",
                "--single-transaction",
                "db_name",
                "--execute",
                "SELECT `column` from `table`;",
            ]
        )
        assert single_result == check_output.return_value.decode.return_value
