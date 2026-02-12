from cryptography.fernet import Fernet
import os

KEY = Fernet.generate_key() 
cipher_suite = Fernet(KEY)

def encrypt_data(data: str) -> bytes:
    return cipher_suite.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    return cipher_suite.decrypt(data).decode()