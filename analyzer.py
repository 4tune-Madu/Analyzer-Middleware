ANALYZERS = {
    "127.0.0.1": {
        "machine_id": 3,
        "name": "Test BS-240",
    },

    "10.0.14.36": {
        "machine_id": 3,
        "name": "Mindray BS-240",
    },

    "10.0.252.239": {
        "machine_id": 11,
        "name": "Shalina Mindray BS-240",
    },
}


def identify_analyzer(ip_address):
    return ANALYZERS.get(ip_address)