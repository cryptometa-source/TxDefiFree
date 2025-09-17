from enum import Enum
import json, base64
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import keyring

class SupportEncryption(Enum):
    AES = 0
    NONE = 1

    @staticmethod
    def to_enum(type_str: str)->Enum:
        if type_str and type_str.upper() == SupportEncryption.AES.name:
            return SupportEncryption.AES
        else:
            return SupportEncryption.NONE
        
class PromptInterface(Enum):
    CLI = 0,
    UI = 1

def get_encryption_password(app_name: str, user_name: str):
    return keyring.get_password(app_name, user_name)   

def set_password(app_name: str, user_name: str, pwd: str):
    keyring.set_password(app_name, user_name, pwd)

def encrypt_wallet_key(private_key_bytes, password, encryption: SupportEncryption):
    salt = get_random_bytes(16)
    key = PBKDF2(password, salt, dkLen=32, count=100_000)
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(private_key_bytes)
    return base64.b64encode(json.dumps({
        'salt': salt.hex(),
        'nonce': cipher.nonce.hex(),
        'tag': tag.hex(),
        'ciphertext': ciphertext.hex()
    }).encode()).decode()

def decrypt_wallet_key(encoded_data, password, encryption: SupportEncryption):
    try:
        data = json.loads(base64.b64decode(encoded_data).decode())
        key = PBKDF2(password, bytes.fromhex(data['salt']), dkLen=32, count=100_000)
        cipher = AES.new(key, AES.MODE_GCM, nonce=bytes.fromhex(data['nonce']))
        return cipher.decrypt_and_verify(bytes.fromhex(data['ciphertext']), bytes.fromhex(data['tag']))
    except Exception as e:
        print("Encryption: " + str(e))
        
def encrypt(decrypted_data: str, encrypton: SupportEncryption)->str | bytes:
    if encrypton == SupportEncryption.NONE:
        return decrypted_data
    
def decrypt(encrypted_data: str, encrypton: SupportEncryption)->str:
    if encrypton == SupportEncryption.NONE:
        return encrypted_data

    return 

# Example usage
if __name__ == "__main__":
    wallet_key = b"my_super_secret_wallet_private_key"

    # Encrypt
    password = get_encryption_password("test", "user")
    encrypted = encrypt_wallet_key(wallet_key, password, SupportEncryption.AES)
    print("Encrypted Key:\n", encrypted)

    decrypted = decrypt_wallet_key(encrypted, password, SupportEncryption.AES)
    print("Decrypted Key:", decrypted.decode())
