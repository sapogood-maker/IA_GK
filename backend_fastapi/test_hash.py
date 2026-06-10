from app.core.security import hash_password

print('Calling hash_password with "Paulo@p01212"')
print('HASHED:', hash_password('Paulo@p01212'))
