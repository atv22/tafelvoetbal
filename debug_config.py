import firestore_service as db
config_ref = db.db.collection("system_config").document("elo_recalc")
doc = config_ref.get()
if doc.exists:
    print(doc.to_dict())
else:
    print("Doc does not exist")
