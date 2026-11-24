
import pyodbc


SERVER = r"DESKTOP-PBP2R45\SQLEXPRESS"
DATABASE = "LUTHLIVE"


def get_connection():
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
    )

    return pyodbc.connect(connection_string)


def get_machine_by_ip(ip_address):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = """
            SELECT
                MachineId,
                MachineName,
                Protocol,
                IPAddress,
                PortNo,
                Status
            FROM dbo.LabMachineMaster
            WHERE IPAddress = ?
        """

        cursor.execute(query, ip_address)
        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "machine_id": row.MachineId,
            "name": row.MachineName,
            "protocol": row.Protocol,
            "ip_address": row.IPAddress,
            "port": row.PortNo,
            "status": row.Status,
        }

    finally:
        connection.close()


def get_samples_by_lab_no(lab_no):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = """
            SELECT
                LabSampleId,
                LabNo,
                ServiceId,
                MachineId,
                isStat,
                Status
            FROM dbo.LabSampleMainIP
            WHERE LabNo = ?
            ORDER BY LabSampleId
        """

        cursor.execute(query, lab_no)

        columns = [
            column[0]
            for column in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_machine_tests_for_services(service_ids, machine_id):
    """
    Resolve LIS ServiceIds into active analyzer tests.

    Supports:
        T = individual test
        P = panel expanded into individual tests

    Returns test mappings ordered by ServiceId, panel SortOrder,
    then ChannelNo.
    """
    service_ids = list(dict.fromkeys(service_ids))

    if not service_ids:
        return []

    placeholders = ", ".join("?" for _ in service_ids)

    query = f"""
        SELECT
            m.ServiceId AS service_id,
            m.MapType AS map_type,
            t.TestId AS test_id,
            t.MachineId AS machine_id,
            t.ChannelNo AS channel_no,
            t.TestCode AS test_code,
            t.ResultName AS result_name,
            t.Unit AS unit,
            t.Status AS status,
            CAST(0 AS smallint) AS sort_order
        FROM dbo.LabServiceMachineMap m
        INNER JOIN dbo.LabMachineTestMaster t
            ON t.TestId = m.TestId
           AND t.MachineId = m.MachineId
        WHERE m.MachineId = ?
          AND m.Status = 1
          AND m.MapType = 'T'
          AND t.Status = 1
          AND m.ServiceId IN ({placeholders})

        UNION ALL

        SELECT
            m.ServiceId AS service_id,
            m.MapType AS map_type,
            t.TestId AS test_id,
            t.MachineId AS machine_id,
            t.ChannelNo AS channel_no,
            t.TestCode AS test_code,
            t.ResultName AS result_name,
            t.Unit AS unit,
            t.Status AS status,
            pt.SortOrder AS sort_order
        FROM dbo.LabServiceMachineMap m
        INNER JOIN dbo.LabMachinePanelMaster p
            ON p.PanelId = m.PanelId
           AND p.MachineId = m.MachineId
        INNER JOIN dbo.LabMachinePanelTest pt
            ON pt.PanelId = p.PanelId
        INNER JOIN dbo.LabMachineTestMaster t
            ON t.TestId = pt.TestId
           AND t.MachineId = m.MachineId
        WHERE m.MachineId = ?
          AND m.Status = 1
          AND m.MapType = 'P'
          AND p.Status = 1
          AND t.Status = 1
          AND m.ServiceId IN ({placeholders})

        ORDER BY service_id, sort_order, channel_no
    """

    params = (
        [machine_id]
        + service_ids
        + [machine_id]
        + service_ids
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(query, params)

        columns = [
            column[0]
            for column in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def lab_no_exists(lab_no):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = """
            SELECT TOP 1 1
            FROM dbo.LabSampleMainIP
            WHERE LabNo = ?
        """

        cursor.execute(query, lab_no)

        return cursor.fetchone() is not None

    finally:
        connection.close()



def get_existing_machine_results(lab_no, machine_id):
    """Inspect existing analyzer results without modifying data."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = """
            SELECT
                Id,
                MachineId,
                HostComputerName,
                LabNo,
                TestCode,
                Result,
                ResultDateTime,
                Reviewed,
                ResultTransmitted,
                Status,
                LastModifiedDate
            FROM dbo.LabInterfaceMachineResult
            WHERE LabNo = ?
              AND MachineId = ?
            ORDER BY TestCode, ResultDateTime, Id
        """

        cursor.execute(query, lab_no, machine_id)

        columns = [
            column[0]
            for column in cursor.description
        ]

        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def get_bs240_test_mapping(channel_no):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT PanelName, ChemistryName, ChannelNo
            FROM dbo.BS240TestMapping
            WHERE ChannelNo = ?
        """, (channel_no,))

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "panel": row[0],
            "chemistry": row[1],
            "channel_no": row[2],
        }

    finally:
        connection.close()

def get_machine_test(machine_id, channel_no):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                TestId,
                MachineId,
                ChannelNo,
                TestCode,
                ResultName,
                Unit,
                Status
            FROM dbo.LabMachineTestMaster
            WHERE MachineId = ?
              AND ChannelNo = ?
        """, (machine_id, channel_no))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "test_id": row[0],
            "machine_id": row[1],
            "channel_no": row[2],
            "test_code": row[3],
            "result_name": row[4],
            "unit": row[5],
            "status": row[6],
        }

    finally:
        connection.close()

def get_machine_test_by_result_name(machine_id, result_name):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                TestId,
                MachineId,
                ChannelNo,
                TestCode,
                ResultName,
                Unit,
                Status
            FROM dbo.LabMachineTestMaster
            WHERE MachineId = ?
              AND LTRIM(RTRIM(ResultName)) = ?
        """, (machine_id, result_name.strip()))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "test_id": row[0],
            "machine_id": row[1],
            "channel_no": row[2],
            "test_code": row[3],
            "result_name": row[4],
            "unit": row[5],
            "status": row[6],
        }

    finally:
        connection.close()



def get_active_machine_test_by_result_name(machine_id, result_name):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                TestId,
                MachineId,
                ChannelNo,
                TestCode,
                ResultName,
                Unit,
                Status
            FROM dbo.LabMachineTestMaster
            WHERE MachineId = ?
              AND LTRIM(RTRIM(ResultName)) = ?
              AND Status = 1
        """, (machine_id, result_name.strip()))

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "test_id": row[0],
            "machine_id": row[1],
            "channel_no": row[2],
            "test_code": row[3],
            "result_name": row[4],
            "unit": row[5],
            "status": row[6],
        }

    finally:
        connection.close()


def machine_result_exists(machine_id, lab_no, test_code):
    """Check whether a result already exists. Read-only."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT TOP 1 Id
            FROM dbo.LabInterfaceMachineResult
            WHERE MachineId = ?
              AND LabNo = ?
              AND TestCode = ?
        """, (machine_id, str(lab_no), test_code))

        return cursor.fetchone() is not None

    finally:
        connection.close()



def insert_machine_result(record):
    """
    Insert one prepared analyzer result into LabInterfaceMachineResult.
    Returns the newly created row ID after a successful commit.
    Raises an exception if the insert fails.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        query = """
            INSERT INTO dbo.LabInterfaceMachineResult (
                MachineId,
                HostComputerName,
                LabNo,
                TestCode,
                Result,
                ResultDateTime,
                Reviewed,
                ResultTransmitted,
                Status,
                LastModifiedDate
            )
            OUTPUT INSERTED.Id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(
            query,
            (
                record["MachineId"],
                record["HostComputerName"],
                str(record["LabNo"]),
                record["TestCode"],
                str(record["Result"]),
                record["ResultDateTime"],
                record["Reviewed"],
                record["ResultTransmitted"],
                record["Status"],
                record["LastModifiedDate"],
            ),
        )

        result = cursor.fetchone()
        inserted_id = result[0]

        connection.commit()

        return inserted_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()




def insert_machine_result_in_transaction(cursor, record):
    """
    Insert one prepared analyzer result using an existing cursor.
    Does not commit or roll back.
    The caller owns the transaction.
    Returns the inserted row ID.
    """

    query = """
        INSERT INTO dbo.LabInterfaceMachineResult (
            MachineId,
            HostComputerName,
            LabNo,
            TestCode,
            Result,
            ResultDateTime,
            Reviewed,
            ResultTransmitted,
            Status,
            LastModifiedDate
        )
        OUTPUT INSERTED.Id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    cursor.execute(
        query,
        (
            record["MachineId"],
            record["HostComputerName"],
            str(record["LabNo"]),
            record["TestCode"],
            str(record["Result"]),
            record["ResultDateTime"],
            record["Reviewed"],
            record["ResultTransmitted"],
            record["Status"],
            record["LastModifiedDate"],
        ),
    )

    result = cursor.fetchone()

    if result is None:
        raise RuntimeError("Insert succeeded without returning a row ID.")

    return result[0]


def get_machine_result_matches(machine_id, lab_no, test_code):
    """
    Return existing records matching a machine, sample, and test.
    Read-only; does not modify database records.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                Id,
                Result,
                ResultDateTime
            FROM dbo.LabInterfaceMachineResult
            WHERE MachineId = ?
              AND LabNo = ?
              AND TestCode = ?
            ORDER BY Id
        """, (machine_id, str(lab_no), test_code))

        rows = cursor.fetchall()

        return [
            {
                "id": row.Id,
                "result": row.Result,
                "result_datetime": row.ResultDateTime,
            }
            for row in rows
        ]

    finally:
        connection.close()
