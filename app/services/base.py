class BaseService:
    def __init__(self, **kwargs):
        self.__db_conn = kwargs.get('db_conn', None)
        self.__repository = kwargs.get('repository', None)
        self.__config = kwargs.get('config', None)

    @property
    def db_conn(self):
        if not self.__db_conn:
            raise Exception('No database connection provided')
        return self.__db_conn

    @db_conn.setter
    def db_conn(self, value):
        self.__db_conn = value

    @property
    def repository(self):
        return self.__repository

    @property
    def config(self):
        if self.__config is None:
            from app.settings import load_config
            self.__config = load_config()
        return self.__config
