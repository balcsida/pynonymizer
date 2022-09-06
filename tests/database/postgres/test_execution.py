import pytest
import unittest
from unittest.mock import patch, Mock, ANY
from pynonymizer.database.exceptions import DependencyError
from pynonymizer.database.postgres.execution import PSqlCmdRunner, PSqlDumpRunner
from tests.helpers import SuperdictOf
import subprocess


@patch("shutil.which", Mock(return_value=None))
class NoExecutablesInPathTests(unittest.TestCase):
    def test_dump_runner_missing_mysqldump(self):
        with pytest.raises(DependencyError):
            PSqlDumpRunner("1.2.3.4", "user", "password", "name")

    def test_cmd_runner_missing_mysql(self):
        with pytest.raises(DependencyError):
            PSqlCmdRunner("1.2.3.4", "user", "password", "name")


@patch("subprocess.Popen")
@patch("subprocess.check_output")
class DumperWithMissingPasswordTests(unittest.TestCase):
    @patch("shutil.which", Mock(return_value="fake/path/to/executable"))
    def setup_method(self, test_method):
        self.dump_runner = PSqlDumpRunner(
            db_host="1.2.3.4",
            db_user="db_user",
            db_pass=None,
            db_name="db_name",
            db_port="5432",
            additional_opts="--quick --other-option=1",
        )

    def test_open_dumper__should_not_pass_pgpassword(self, check_output, popen):
        open_result = self.dump_runner.open_dumper()

        popen.assert_called()
        popen.assert_not_called_with(
            ANY,
            env=SuperdictOf({"PGPASSWORD": ANY}),
            stdout=ANY,
        )


@patch("subprocess.Popen")
@patch("subprocess.check_output")
class DumperTests(unittest.TestCase):
    @patch("shutil.which", Mock(return_value="fake/path/to/executable"))
    def setup_method(self, test_method):
        self.dump_runner = PSqlDumpRunner(
            db_host="1.2.3.4",
            db_user="db_user",
            db_pass="db_password",
            db_name="db_name",
            db_port="5432",
            additional_opts="--quick --other-option=1",
        )

    def test_open_dumper__should_open_pipe_to_pgdump(self, check_output, popen):
        open_result = self.dump_runner.open_dumper()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "pg_dump",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--quick",
                "--other-option=1",
                "db_name",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
            stdout=subprocess.PIPE,
        )

        # dumper should return the stdout of that process
        assert open_result == popen.return_value.stdout


@patch("subprocess.Popen")
@patch("subprocess.check_output")
class CmdWithAllArgsTets(unittest.TestCase):
    @patch("shutil.which", Mock(return_value="fake/path/to/executable"))
    def setup_method(self, test_method):
        self.cmd_runner = PSqlCmdRunner(
            db_host="1.2.3.4",
            db_user="db_user",
            db_pass=None,
            db_name="db_name",
            db_port="5432",
            additional_opts="--quick --other-option=1",
        )

    def test_open_batch_processor__should_not_pass_pgpassword(
        self, check_output, popen
    ):
        open_result = self.cmd_runner.open_batch_processor()

        popen.assert_called()
        popen.assert_not_called_with(
            ANY,
            env=SuperdictOf({"PGPASSWORD": ANY}),
            stdin=ANY,
        )

    def test_execute__should_not_pass_pgpassword(self, check_output, popen):
        execute_result = self.cmd_runner.execute("SELECT `column` from `table`;")

        check_output.assert_called()
        check_output.assert_not_called_with(ANY, env=SuperdictOf({"PGPASSWORD": ANY}))

    def test_execute_list__should_not_pass_pgpassword(self, check_output, popen):
        execute_result = self.cmd_runner.execute(
            ["SELECT `column` from `table`;", "SELECT `column2` from `table2`;"]
        )

        check_output.assert_called()
        check_output.assert_not_called_with(ANY, env=SuperdictOf({"PGPASSWORD": ANY}))


@patch("subprocess.Popen")
@patch("subprocess.check_output")
class CmdTests(unittest.TestCase):
    @patch("shutil.which", Mock(return_value="fake/path/to/executable"))
    def setup_method(self, test_method):
        self.cmd_runner = PSqlCmdRunner(
            "1.2.3.4",
            "db_user",
            "db_password",
            "db_name",
            db_port="5432",
            additional_opts="--quick --other-option=1",
        )

    def test_open_batch_processor__should_open_psql_pipe(self, check_output, popen):
        open_result = self.cmd_runner.open_batch_processor()

        # dumper should open a process for the current db dump, piping stdout for processing
        popen.assert_called_with(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--dbname",
                "db_name",
                "--quiet",
                "--quick",
                "--other-option=1",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
            stdin=subprocess.PIPE,
        )

        # dumper should return the stdin of that process
        assert open_result == popen.return_value.stdin

    def test_execute(self, check_output, popen):
        execute_result = self.cmd_runner.execute("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column` from `table`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )

    def test_execute_list(self, check_output, popen):
        execute_result = self.cmd_runner.execute(
            ["SELECT `column` from `table`;", "SELECT `column2` from `table2`;"]
        )

        check_output.assert_any_call(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column` from `table`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )

        check_output.assert_any_call(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column2` from `table2`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )

    def test_db_execute(self, check_output, popen):
        """
        execute should execute an arbitrary statement with valid args
        """
        execute_result = self.cmd_runner.db_execute("SELECT `column` from `table`;")

        check_output.assert_called_with(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--dbname",
                "db_name",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column` from `table`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )

    def test_db_execute_list(self, check_output, popen):
        execute_result = self.cmd_runner.db_execute(
            ["SELECT `column` from `table`;", "SELECT `column2` from `table2`;"]
        )

        check_output.assert_any_call(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--dbname",
                "db_name",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column` from `table`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )
        check_output.assert_any_call(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--dbname",
                "db_name",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column2` from `table2`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )

    def test_get_single_result(self, check_output, popen):
        """
        execute should execute an arbitrary statement and return the decoded, no-column result
        """
        single_result = self.cmd_runner.get_single_result(
            "SELECT `column` from `table`;"
        )

        check_output.assert_called_with(
            [
                "psql",
                "--host",
                "1.2.3.4",
                "--port",
                "5432",
                "--username",
                "db_user",
                "--dbname",
                "db_name",
                "-tA",
                "--quick",
                "--other-option=1",
                "--command",
                "SELECT `column` from `table`;",
            ],
            env=SuperdictOf({"PGPASSWORD": "db_password"}),
        )
        assert single_result == check_output.return_value.decode.return_value
