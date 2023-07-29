"""
Versioning for StudentVue Data Viewer
Licensed under the Unlicense (P.D.)
2023-07-24
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from base64 import urlsafe_b64encode
from shutil import rmtree
from os import unlink
from typing import Optional
from json import dump, load, dumps, loads
from hashlib import sha256
from dacite import from_dict as dataclass_from_dict
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from config_parser import parse
from tools import VersioningMismatchedCredentialsException, InvalidCredentialsException
from common import VERSIONING_PATH, VERSIONS_FILENAME, HASH_FILENAME, Logger


### Dataclasses ###
@dataclass
class VersioningCourseItem:
    """A course for the versioning item"""

    name: str
    grade: int


@dataclass
class VersioningItem:
    """A versioning item that is shown to the user"""

    courses: list[VersioningCourseItem]
    timestamp: int


@dataclass
class HashData:
    """Hash data"""

    key: bytes
    hash: bytes


class Versioning:
    """Versioning / past grade history. All version history is encrypted as follows:
    f"{password}{master_key}{username}{password[::-1]}".
    The hashes, on the other hand, are calculated as follows:
    f"{username}{password}{master_key}"

    This encryption scheme is probably very scuffed. At least we can ensure that the
    password hashes will always be different for different users since the username
    is in the hash function, but we don't use any *unique* salt.
    """

    def __init__(
        self,
        username: str,
        password: str,
        serialized: Optional["GradebookInformation"] = None,
    ):
        self.username: str = username
        self.password: str = password
        self.serialized: Optional["GradebookInformation"] = serialized
        self.files: list[str] = []
        self.path: Path = (
            VERSIONING_PATH / sha256(bytes(self.username, "utf-8")).hexdigest()
        )
        self.master_key: str = parse()["master_key"]

        self.mkdir()

        self.hash_data: HashData = self._load_hash_data()
        self.fernet: Fernet = self._get_fernet(self.hash_data.key)

    def load(self, timestamp: int):
        """Load the gradebook from the timestamp."""

        # fmt:off
        from gradebook import GradebookInformation  # pylint:disable=import-outside-toplevel
        # fmt:on

        try:
            with open(self.path / f"{timestamp}", "rb") as gradebook_file:
                encrypted_gradebook: bytes = gradebook_file.read()
                decrypted = self.fernet.decrypt(encrypted_gradebook).decode("utf-8")
                gradebook_dict: dict = loads(decrypted)
            gradebook: GradebookInformation = dataclass_from_dict(
                data_class=GradebookInformation, data=gradebook_dict
            )
        except InvalidToken as err:
            raise InvalidCredentialsException() from err
        return gradebook

    def save(self) -> None:
        """Save the gradebook into the user's versioning directory.

        Two files are saved in this process:
        "<timestamp>.json" is saved with the full serialized JSON tree, and
        "VERSIONS.json" is "appended" to have a brief overview of the gradebook
        state (:class:`VersioningItem`).

        All files are encrypted with the key, the hashed variant of which is found in "HASH.txt". Should the hash
        change, this will raise :class:`VersioningMismatchedCredentialsException`.
        """

        self._check_credentials(self.hash_data)
        self._save_gradebook(self.serialized)
        versioning_list: list[VersioningItem] = self.list_history()
        versioning_list.append(
            VersioningItem(
                timestamp=self.serialized.last_updated,
                courses=[
                    VersioningCourseItem(course.name, course.grade)
                    for course in self.serialized.grades
                ],
            )
        )
        self._save_versioning_list(versioning_list=versioning_list)

    def list_history(self) -> list[VersioningItem]:
        """Return a list of version items"""

        versioning_list: list[dict]
        try:
            with open(self.path / VERSIONS_FILENAME, "rb") as versions_file:
                encrypted_versions: bytes = versions_file.read()
                decrypted = self.fernet.decrypt(encrypted_versions).decode("utf-8")
                versioning_list: list[dict] = loads(decrypted)
        except FileNotFoundError:
            versioning_list: list = []
        except InvalidToken as err:
            raise InvalidCredentialsException() from err
        for idx, version_item_dict in enumerate(versioning_list):
            versioning_list[idx] = dataclass_from_dict(
                data_class=VersioningItem, data=version_item_dict
            )
        return versioning_list

    def migrate(self, old_password: str, new_password: str):
        """Migrate everything for a user from an old password to a new password"""

        def _update_encryption(password: str):
            self.password: str = password
            self.hash_data: HashData = self._load_hash_data(force=True)
            self.fernet: Fernet = self._get_fernet(self.hash_data.key)

        # Set decryption to use the old password
        _update_encryption(old_password)
        self._check_credentials(self.hash_data)

        # Load all files
        gradebook_files: list = []  # In the same order as the versioning list
        versioning_list: list[VersioningItem] = self.list_history()
        version: VersioningItem
        for version in versioning_list:
            gradebook_files.append(self.load(version.timestamp))

        # Set encryption to use the new password
        _update_encryption(new_password)
        self._load_hash_data()

        # Save all files
        self._save_versioning_list(versioning_list)
        for gradebook in gradebook_files:
            # Deleting is probably not needed
            # self.remove_gradebook_entry(version.timestamp, update_versioning_list=False)
            self._save_gradebook(gradebook)

    @staticmethod
    def remove_user_data(username: str):
        """Remove the user directory"""

        rmtree(VERSIONING_PATH / sha256(bytes(username, "utf-8")).hexdigest())

    def remove_gradebook_entry(
        self, timestamp: int, update_versioning_list: bool = True
    ):
        """Remove a gradebook entry, potentially updating the version list"""

        unlink(self.path / f"{timestamp}")

        if not update_versioning_list:
            return
        versioning_list: list[VersioningItem] = self.list_history()
        delete_idx: int
        for idx, version in enumerate(versioning_list):
            if version.timestamp == timestamp:
                delete_idx: int = idx
                break
        else:
            return
        versioning_list.pop(delete_idx)
        self._save_versioning_list(versioning_list)

    @staticmethod
    def hash_for_user(username: str):
        """Returns the hash for a user"""

        read_hash: str
        with open(
            VERSIONING_PATH
            / sha256(bytes(username, "utf-8")).hexdigest()
            / HASH_FILENAME,
            "r",
            encoding="utf-8",
        ) as hash_file:
            read_hash: str = hash_file.read()

        return read_hash

    def _check_credentials(self, hash_data: HashData):
        """Raises an exception if the credentials do not match"""

        if self.hash != hash_data.hash:
            Logger.fatal(f"Hash {self.hash} did not match {hash_data.hash}")
            raise VersioningMismatchedCredentialsException()

    def _get_fernet(self, key: bytes) -> Fernet:
        return Fernet(key=key)

    def _load_hash_data(self, force: bool = False) -> HashData:
        """Load hash data from the hash file, or, if unavailable, create a new file
        with the hash data. The hash data is returned as: {"key": bytes, "hash": str}
        """

        hash_data: HashData = self._new_hash_data()  # Only for key if file is loaded
        try:
            if force:
                raise FileNotFoundError()
            hash_data.hash: str = self.hash_for_user(self.username)
        except FileNotFoundError:  # KeyError for above
            self._save_hash_data(hash_data)

        return hash_data

    def _save_hash_data(self, hash_data: HashData):
        with open(self.path / HASH_FILENAME, "w", encoding="utf-8") as hash_file:
            hash_file.seek(0)  # Pointless
            hash_file.truncate(0)  # Also probably pointless (it never changes size)
            hash_file.write(hash_data.hash)

    def _save_gradebook(self, gradebook):
        encrypted_serialized: bytes = self.fernet.encrypt(
            bytes(dumps(asdict(gradebook)), "utf-8")
        )
        with open(self.path / f"{gradebook.last_updated}", "wb") as grade_file:
            grade_file.seek(0)  # Pointless
            grade_file.truncate(0)  # May be an existing file
            grade_file.write(encrypted_serialized)

    def _save_versioning_list(self, versioning_list: list[VersioningItem]):
        encrypted_versioning_list: bytes = self.fernet.encrypt(
            bytes(
                dumps([asdict(versioning_item) for versioning_item in versioning_list]),
                "utf-8",
            )
        )
        with open(self.path / VERSIONS_FILENAME, "wb") as versions_file:
            versions_file.seek(0)  # Pointless
            versions_file.truncate(0)  # Also probably pointless, we expand size
            versions_file.write(encrypted_versioning_list)

    @property
    def hash(self) -> str:
        """:meth:`self.hash_generic` on our values"""

        return self.hash_generic(self.username, self.password, self.master_key)

    @staticmethod
    def hash_generic(username: str, password: str, master_key: str):
        """Return a hash with the username, password, and encryption master key"""

        return sha256(
            bytes(f"{username}{password}{master_key}", "utf-8"),
        ).hexdigest()

    def key_hash(self, password: str) -> str:
        """Returns a hash used for the key"""

        return sha256(
            bytes(
                f"{password}{self.master_key}{self.username}{password[::-1]}",
                "utf-8",
            ),
        ).hexdigest()

    def _new_hash_data(self) -> HashData:
        """Return hash data"""

        salt: bytes = bytes(self.master_key, "utf-8")
        kdf: PBKDF2HMAC = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key: bytes = bytes(self.key_hash(self.password), "ASCII")
        key: bytes = urlsafe_b64encode(kdf.derive(key))

        return HashData(key, hash=self.hash)

    def mkdir(self):
        """Make the user versioning history directory"""

        self.path.mkdir(parents=True, exist_ok=True)
