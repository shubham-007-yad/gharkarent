import auth

def test_auth():
    password = "Admin@007"
    print(f"Testing with password: {password}")
    
    hashed = auth.get_password_hash(password)
    print(f"Hashed: {hashed}")
    
    is_valid = auth.verify_password(password, hashed)
    print(f"Verification result: {is_valid}")
    
    if is_valid:
        print("Auth logic is WORKING correctly!")
    else:
        print("Auth logic is BROKEN!")

if __name__ == "__main__":
    test_auth()
