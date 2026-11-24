class HL7Message:
    def __init__(self, raw_message):
        self.raw_message = raw_message

        # HL7 messages normally use carriage return
        # between segments.
        self.segments = raw_message.split("\r")

    def get_segment(self, segment_name):
        for segment in self.segments:
            fields = segment.split("|")

            if fields[0] == segment_name:
                return fields

        return None

    def get_field(self, segment_name, field_number):
        segment = self.get_segment(segment_name)

        if segment is None:
            return None

        if field_number >= len(segment):
            return None

        return segment[field_number]


    def get_segments(self, segment_name):
        """Return all segments matching the given name."""

        return [
            segment.split("|")
            for segment in self.segments
            if segment.startswith(f"{segment_name}|")
        ]


    def get_observation_results(self):
        """Extract raw OBX observation fields."""

        results = []

        for obx in self.get_segments("OBX"):
            observation = {
                "set_id": obx[1] if len(obx) > 1 else None,
                "value_type": obx[2] if len(obx) > 2 else None,
                "test_code": obx[3] if len(obx) > 3 else None,
                "test_name": obx[4] if len(obx) > 4 else None,
                "result": obx[5] if len(obx) > 5 else None,
                "unit": obx[6] if len(obx) > 6 else None,
                "reference_range": obx[7] if len(obx) > 7 else None,
                "abnormal_flag": obx[8] if len(obx) > 8 else None,
                "status": obx[11] if len(obx) > 11 else None,
                "original_result": obx[13] if len(obx) > 13 else None,
                "result_datetime": obx[14] if len(obx) > 14 else None,
            }

            result_value = (observation["result"] or "").strip()
            result_datetime = (observation["result_datetime"] or "").strip()

            observation["is_placeholder"] = (
                result_value == "-268435455.000000"
                and result_datetime == "19000101000000"
            )

            results.append(observation)

        return results

    @property
    def message_type(self):
        return self.get_field("MSH", 8)

    @property
    def control_id(self):
        return self.get_field("MSH", 9)


    def get_lab_no(self):
        """Extract LabNo from the OBR segment."""

        return self.get_field("OBR", 2)




    def validate_result_message(self):
        """
        Validate message-level requirements for an ORU^R01 result message.
    
        Individual OBX observations are validated separately so one
        invalid observation does not automatically invalidate the batch.
        """
    
        errors = []
    
        if self.get_segment("OBR") is None:
            errors.append("Missing OBR segment.")
    
        lab_no = self.get_lab_no()
    
        if not lab_no:
            errors.append("Missing LabNo in OBR-2.")
    
        observations = self.get_observation_results()
    
        if not observations:
            errors.append("No OBX observation segments found.")
    
        return errors
    
    def get_result_datetime(self):
        """Extract the result timestamp from OBR-7."""
        return self.get_field("OBR", 7)
        