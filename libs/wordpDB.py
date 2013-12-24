import MySQLdb
class DB:
    conn = None

    def connect(self):
        self.conn = MySQLdb.connect(host='127.0.0.1',user='wordp',passwd='magic',port=3306, db='wordp')
        self.conn.set_character_set('utf8')
        cursor = self.conn.cursor()
        cursor.execute('set names utf8')
        cursor.close()

    def query(self, sql, cursor=None):
        try:
            if cursor is None:
                cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(sql)
        except (AttributeError, MySQLdb.OperationalError):
            self.connect()
            cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(sql)
        return cursor

