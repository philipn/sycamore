import MySQLdb
db = MySQLdb.connect(host="localhost", user="root", db="test")
cursor = db.cursor()
cursor.executemany("""INSERT into fun values (%s)""", ('poo'))
cursor.close()
db.close()
