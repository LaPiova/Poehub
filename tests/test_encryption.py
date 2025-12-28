import base64

from cryptography.fernet import Fernet

from poehub.encryption import EncryptionHelper, generate_key


class TestEncryptionHelper:
    def test_init_generates_key(self):
        helper = EncryptionHelper()
        assert helper.get_key() is not None
        assert isinstance(helper.get_key(), str)

    def test_init_with_provided_key(self):
        key = Fernet.generate_key().decode()
        helper = EncryptionHelper(key=key)
        assert helper.get_key() == key

    def test_encrypt_decrypt_string(self):
        helper = EncryptionHelper()
        original_data = "test_string"
        encrypted = helper.encrypt(original_data)
        assert encrypted != original_data
        decrypted = helper.decrypt(encrypted)
        assert decrypted == original_data

    def test_encrypt_decrypt_dict(self):
        helper = EncryptionHelper()
        original_data = {"key": "value", "number": 123}
        encrypted = helper.encrypt(original_data)
        decrypted = helper.decrypt(encrypted)
        assert decrypted == original_data

    def test_encrypt_none(self):
        helper = EncryptionHelper()
        assert helper.encrypt(None) is None

    def test_decrypt_none(self):
        helper = EncryptionHelper()
        assert helper.decrypt(None) is None

    def test_decrypt_invalid_data(self):
        helper = EncryptionHelper()
        assert helper.decrypt("invalid_base64_string") is None

        # Valid base64 but invalid fernet token
        invalid_token = base64.b64encode(b"not a valid token").decode()
        assert helper.decrypt(invalid_token) is None

    def test_encrypt_dict_helper(self):
        helper = EncryptionHelper()
        data = {"field1": "value1", "field2": 100}
        encrypted_dict = helper.encrypt_dict(data)

        assert "field1" in encrypted_dict
        assert "field2" in encrypted_dict
        assert encrypted_dict["field1"] != "value1"

        decrypted_dict = helper.decrypt_dict(encrypted_dict)
        assert decrypted_dict == data

    def test_encrypt_dict_empty(self):
        helper = EncryptionHelper()
        assert helper.encrypt_dict({}) == {}

    def test_decrypt_dict_empty(self):
        helper = EncryptionHelper()
        assert helper.decrypt_dict({}) == {}


def test_generate_key_function():
    key = generate_key()
    assert isinstance(key, str)
    # verify it's a valid fernet key
    Fernet(key.encode())
