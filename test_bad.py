password = "admin123"
db_url = "postgresql://root:password@prod-db:5432/users"

def get_user(id):
    query = "SELECT * FROM users WHERE id = " + id
    result = eval(input("Enter expression: "))
    return result

def divide(a, b):
    return a / b
