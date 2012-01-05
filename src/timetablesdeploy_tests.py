#!/usr/bin/env python
import unittest, os.path, shutil, tempfile, timetablesdeploy
from contextlib import contextmanager

@contextmanager
def deploy(arg_string):
    argv = arg_string.split(" ")
    deployed_path = timetablesdeploy.run(argv)
    yield deployed_path
    shutil.rmtree(deployed_path)

class TestTimetablesDeploy(unittest.TestCase):
    
    def setUp(self):
        self.data_dir = tempfile.mkdtemp()
        for i in range(10): tempfile.mkstemp(dir=self.data_dir)
        
        self.config_file = tempfile.mkstemp()[1]
        with open(self.config_file, "w") as c:
            c.write("This is the test config file.")
    
    def tearDown(self):
        shutil.rmtree(self.data_dir, ignore_errors=True)
        os.unlink(self.config_file)
    
    def test_deploy(self):
        with deploy("--source https://github.com/h4l/timetables.git " +
                    "--tag 2012-01-05T1038 " +
                    "--data {0} ".format(self.data_dir) +
                    "--config {0} ".format(self.config_file) +
                    "/tmp/") as path:
            self.assertTrue(os.path.isdir(path))
    
    def test_create_temp_directory(self):
        path = timetablesdeploy.create_temp_directory()
        self.assertTrue(os.path.isdir(path))
        self.assertEqual(os.listdir(path), [])
        os.rmdir(path)
        self.assertFalse(os.path.exists(path))

if __name__ == "__main__":
    unittest.main()