"""Configuration module for running tests with pytest"""


def pytest_addoption(parser):
    group = parser.getgroup("straditize", "straditize specific options")
    group.addoption('--nrandom',
                    help='Set the number of generated random samples',
                    default=20, type=int)


def pytest_configure(config):
    import test_binary
    test_binary.DataReaderTest.nsamples = config.getoption('nrandom')
