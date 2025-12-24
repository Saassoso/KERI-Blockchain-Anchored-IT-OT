from keri.app import habbing
from keri.app import storing
import os

base_folder = "./keri_data"
if not os.path.exists(base_folder):
    os.makedirs(base_folder)

# Use FileStore backend
store = storing.FileStore(base_folder)
habery = habbing.Habery(name="test", base=base_folder, temp=True, db=store)

hab = habery.makeHab(name="almbq", isith="1", icount=1)
print("New Hab created!")
print("AID:", hab.pre)
print("Signing key:", hab.kever.verfers[0].qb64)

# Close to persist
habery.db.close()
print("Hab saved to disk.")
