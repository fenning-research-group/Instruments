## module for communication with Omega temperature controller

import serial
import numpy as np
import codecs

class tec:
	def __init__(self, port = 'COM12', address = 1):
		self.connect(port = port, address = address)	


	def connect(self, port = 'COM12', address = 1):
		self.__handle = serial.rs485.RS485(port = port)
		self.__handle.rs485_mode = serial.rs485.RS485Settings(True, False)
		
		#configure communication bits
		self.__address = codecs.encode(str.encode('{0:02d}'.format(address)), 'hex_codec')	#convert to hex, for use in communication <addr>
		self.__start = b'02'	#start bit <stx>
		self.__filter = b'4C'	#filter character, hex representation of "L"
		self.__end = b'03'	#end bit <etx>

		return True

	def disconnect(self):
		self.__handle.close()
		return True


	### helper methods

	def _create_payload(
		functioncode,
		registeraddress,
		value,
		number_of_decimals,
		number_of_registers,
		number_of_bits,
		signed,
		byteorder,
		payloadformat,
	):
		"""Create the payload.
		Error checking should have been done before calling this function.
		For argument descriptions, see the _generic_command() method.
		"""
		if functioncode in [1, 2]:
			return _num_to_twobyte_string(registeraddress) + _num_to_twobyte_string(
				number_of_bits
			)
		if functioncode in [3, 4]:
			return _num_to_twobyte_string(registeraddress) + _num_to_twobyte_string(
				number_of_registers
			)
		if functioncode == 5:
			return _num_to_twobyte_string(registeraddress) + _bit_to_bytestring(value)
		if functioncode == 6:
			return _num_to_twobyte_string(registeraddress) + _num_to_twobyte_string(
				value, number_of_decimals, signed=signed
			)
		if functioncode == 15:
			if payloadformat == _PAYLOADFORMAT_BIT:
				bitlist = [value]
			else:
				bitlist = value
			return (
				_num_to_twobyte_string(registeraddress)
				+ _num_to_twobyte_string(number_of_bits)
				+ _num_to_onebyte_string(
					_calculate_number_of_bytes_for_bits(number_of_bits)
				)
				+ _bits_to_bytestring(bitlist)
			)
		if functioncode == 16:
			if payloadformat == _PAYLOADFORMAT_REGISTER:
				registerdata = _num_to_twobyte_string(
					value, number_of_decimals, signed=signed
				)
			elif payloadformat == _PAYLOADFORMAT_STRING:
				registerdata = _textstring_to_bytestring(value, number_of_registers)
			elif payloadformat == _PAYLOADFORMAT_LONG:
				registerdata = _long_to_bytestring(
					value, signed, number_of_registers, byteorder
				)
			elif payloadformat == _PAYLOADFORMAT_FLOAT:
				registerdata = _float_to_bytestring(value, number_of_registers, byteorder)
			elif payloadformat == _PAYLOADFORMAT_REGISTERS:
				registerdata = _valuelist_to_bytestring(value, number_of_registers)

			assert len(registerdata) == number_of_registers * _NUMBER_OF_BYTES_PER_REGISTER

			return (
				_num_to_twobyte_string(registeraddress)
				+ _num_to_twobyte_string(number_of_registers)
				+ _num_to_onebyte_string(len(registerdata))
				+ registerdata
			)
		raise ValueError("Wrong function code: " + str(functioncode))

	def _parse_payload(
		payload,
		functioncode,
		registeraddress,
		value,
		number_of_decimals,
		number_of_registers,
		number_of_bits,
		signed,
		byteorder,
		payloadformat,
	):
		_check_response_payload(
			payload,
			functioncode,
			registeraddress,
			value,
			number_of_decimals,
			number_of_registers,
			number_of_bits,
			signed,
			byteorder,
			payloadformat,
		)

		if functioncode in [1, 2]:
			registerdata = payload[_NUMBER_OF_BYTES_BEFORE_REGISTERDATA:]
			if payloadformat == _PAYLOADFORMAT_BIT:
				return _bytestring_to_bits(registerdata, number_of_bits)[0]
			elif payloadformat == _PAYLOADFORMAT_BITS:
				return _bytestring_to_bits(registerdata, number_of_bits)

		if functioncode in [3, 4]:
			registerdata = payload[_NUMBER_OF_BYTES_BEFORE_REGISTERDATA:]
			if payloadformat == _PAYLOADFORMAT_STRING:
				return _bytestring_to_textstring(registerdata, number_of_registers)

			elif payloadformat == _PAYLOADFORMAT_LONG:
				return _bytestring_to_long(
					registerdata, signed, number_of_registers, byteorder
				)

			elif payloadformat == _PAYLOADFORMAT_FLOAT:
				return _bytestring_to_float(registerdata, number_of_registers, byteorder)

			elif payloadformat == _PAYLOADFORMAT_REGISTERS:
				return _bytestring_to_valuelist(registerdata, number_of_registers)

			elif payloadformat == _PAYLOADFORMAT_REGISTER:
				return _twobyte_string_to_num(
					registerdata, number_of_decimals, signed=signed
				)


	def _extract_payload(response, slaveaddress, mode, functioncode):
	"""Extract the payload data part from the slave's response.
	Args:
		* response (str): The raw response byte string from the slave.
		  This is different for RTU and ASCII.
		* slaveaddress (int): The adress of the slave. Used here for error checking only.
		* mode (str): The modbus protcol mode (MODE_RTU or MODE_ASCII)
		* functioncode (int): Used here for error checking only.
	Returns:
		The payload part of the *response* string. Conversion from Modbus ASCII
		has been done if applicable.
	Raises:
		ValueError, TypeError, ModbusException (or subclasses).
	Raises an exception if there is any problem with the received address,
	the functioncode or the CRC.
	The received response should have the format:
	* RTU Mode: slaveaddress byte + functioncode byte + payloaddata + CRC (which is two bytes)
	* ASCII Mode: header (:) + slaveaddress byte + functioncode byte +
	  payloaddata + LRC (which is two characters) + footer (CRLF)
	For development purposes, this function can also be used to extract the payload
	from the request sent TO the slave.
	"""
	# Number of bytes before the response payload (in stripped response)
		NUMBER_OF_RESPONSE_STARTBYTES = 2

		NUMBER_OF_CRC_BYTES = 2
		NUMBER_OF_LRC_BYTES = 1
		MINIMAL_RESPONSE_LENGTH_RTU = NUMBER_OF_RESPONSE_STARTBYTES + NUMBER_OF_CRC_BYTES
		MINIMAL_RESPONSE_LENGTH_ASCII = 9

		# Argument validity testing (ValueError/TypeError at lib programming error)
		_check_string(response, description="response")
		_check_slaveaddress(slaveaddress)
		_check_mode(mode)
		_check_functioncode(functioncode, None)

		plainresponse = response

		# Validate response length
		if mode == MODE_ASCII:
			if len(response) < MINIMAL_RESPONSE_LENGTH_ASCII:
				raise InvalidResponseError(
					"Too short Modbus ASCII response (minimum length {} bytes). Response: {!r}".format(
						MINIMAL_RESPONSE_LENGTH_ASCII, response
					)
				)
		elif len(response) < MINIMAL_RESPONSE_LENGTH_RTU:
			raise InvalidResponseError(
				"Too short Modbus RTU response (minimum length {} bytes). Response: {!r}".format(
					MINIMAL_RESPONSE_LENGTH_RTU, response
				)
			)

		if mode == MODE_ASCII:

			# Validate the ASCII header and footer.
			if response[_BYTEPOSITION_FOR_ASCII_HEADER] != _ASCII_HEADER:
				raise InvalidResponseError(
					"Did not find header "
					+ "({!r}) as start of ASCII response. The plain response is: {!r}".format(
						_ASCII_HEADER, response
					)
				)
			elif response[-len(_ASCII_FOOTER) :] != _ASCII_FOOTER:
				raise InvalidResponseError(
					"Did not find footer "
					+ "({!r}) as end of ASCII response. The plain response is: {!r}".format(
						_ASCII_FOOTER, response
					)
				)

			# Strip ASCII header and footer
			response = response[1:-2]

			if len(response) % 2 != 0:
				template = (
					"Stripped ASCII frames should have an even number of bytes, but is {} bytes. "
					+ "The stripped response is: {!r} (plain response: {!r})"
				)
				raise InvalidResponseError(
					template.format(len(response), response, plainresponse)
				)

			# Convert the ASCII (stripped) response string to RTU-like response string
			response = _hexdecode(response)

		# Validate response checksum
		if mode == MODE_ASCII:
			calculate_checksum = _calculate_lrc_string
			number_of_checksum_bytes = NUMBER_OF_LRC_BYTES
		else:
			calculate_checksum = _calculate_crc_string
			number_of_checksum_bytes = NUMBER_OF_CRC_BYTES

		received_checksum = response[-number_of_checksum_bytes:]
		response_without_checksum = response[0 : (len(response) - number_of_checksum_bytes)]
		calculated_checksum = calculate_checksum(response_without_checksum)

		if received_checksum != calculated_checksum:
			template = (
				"Checksum error in {} mode: {!r} instead of {!r} . The response "
				+ "is: {!r} (plain response: {!r})"
			)
			text = template.format(
				mode, received_checksum, calculated_checksum, response, plainresponse
			)
			raise InvalidResponseError(text)

		# Check slave address
		responseaddress = ord(response[_BYTEPOSITION_FOR_SLAVEADDRESS])

		if responseaddress != slaveaddress:
			raise InvalidResponseError(
				"Wrong return slave address: {} instead of {}. The response is: {!r}".format(
					responseaddress, slaveaddress, response
				)
			)

		# Check if slave indicates error
		_check_response_slaveerrorcode(response)

		# Check function code
		received_functioncode = ord(response[_BYTEPOSITION_FOR_FUNCTIONCODE])
		if received_functioncode != functioncode:
			raise InvalidResponseError(
				"Wrong functioncode: {} instead of {}. The response is: {!r}".format(
					received_functioncode, functioncode, response
				)
			)

		# Read data payload
		first_databyte_number = NUMBER_OF_RESPONSE_STARTBYTES

		if mode == MODE_ASCII:
			last_databyte_number = len(response) - NUMBER_OF_LRC_BYTES
		else:
			last_databyte_number = len(response) - NUMBER_OF_CRC_BYTES

		payload = response[first_databyte_number:last_databyte_number]
		return payload
	

	 def _perform_command(self, functioncode, payload_to_slave):
        """Perform the command having the *functioncode*.
        Args:
            * functioncode (int): The function code for the command to be performed.
              Can for example be 'Write register' = 16.
            * payload_to_slave (str): Data to be transmitted to the slave (will be
              embedded in slaveaddress, CRC etc)
        Returns:
            The extracted data payload from the slave (a string). It has been
            stripped of CRC etc.
        Raises:
            TypeError, ValueError, ModbusException,
            serial.SerialException (inherited from IOError)
        Makes use of the :meth:`_communicate` method. The request is generated
        with the :func:`_embed_payload` function, and the parsing of the
        response is done with the :func:`_extract_payload` function.
        """
        DEFAULT_NUMBER_OF_BYTES_TO_READ = 1000

        _check_functioncode(functioncode, None)
        _check_string(payload_to_slave, description="payload")

        # Build request
        request = _embed_payload(
            self.address, self.mode, functioncode, payload_to_slave
        )

        # Calculate number of bytes to read
        number_of_bytes_to_read = DEFAULT_NUMBER_OF_BYTES_TO_READ
        if self.precalculate_read_size:
            try:
                number_of_bytes_to_read = _predict_response_size(
                    self.mode, functioncode, payload_to_slave
                )
            except Exception:
                if self.debug:
                    template = (
                        "Could not precalculate response size for Modbus {} mode. "
                        + "Will read {} bytes. Request: {!r}"
                    )
                    self._print_debug(
                        template.format(self.mode, number_of_bytes_to_read, request)
                    )

        # Communicate
        response = self._communicate(request, number_of_bytes_to_read)

        # Extract payload
        payload_from_slave = _extract_payload(
            response, self.address, self.mode, functioncode
        )
        return payload_from_slave

    def _communicate(self, request, number_of_bytes_to_read):
        """Talk to the slave via a serial port.
        Args:
            request (str): The raw request that is to be sent to the slave.
            number_of_bytes_to_read (int): number of bytes to read
        Returns:
            The raw data (string) returned from the slave.
        Raises:
            TypeError, ValueError, ModbusException,
            serial.SerialException (inherited from IOError)
        Note that the answer might have strange ASCII control signs, which
        makes it difficult to print it in the promt (messes up a bit).
        Use repr() to make the string printable (shows ASCII values for control signs.)
        Will block until reaching *number_of_bytes_to_read* or timeout.
        If the attribute :attr:`Instrument.debug` is :const:`True`, the communication
        details are printed.
        If the attribute :attr:`Instrument.close_port_after_each_call` is :const:`True` the
        serial port is closed after each call.
        Timing::
                            Request from master (Master is writing)
                            |
                            |                             Response from slave (Master is reading)
                            |                             |
            --------R-------W-----------------------------R-------W-----------------------------
                     |     |                               |
                     |     |<------- Roundtrip time ------>|
                     |     |
                  -->|-----|<----- Silent period
        The resolution for Python's time.time() is lower on Windows than on Linux.
        It is about 16 ms on Windows according to
        https://stackoverflow.com/questions/157359/accurate-timestamping-in-python-logging
        For Python3, the information sent to and from pySerial should be of the type bytes.
        This is taken care of automatically by MinimalModbus.
        """
        _check_string(request, minlength=1, description="request")
        _check_int(number_of_bytes_to_read)

        self._print_debug(
            "Will write to instrument (expecting {} bytes back): {!r} ({})".format(
                number_of_bytes_to_read, request, _hexlify(request)
            )
        )

        if not self.serial.is_open:
            self._print_debug("Opening port {}".format(self.serial.port))
            self.serial.open()

        if self.clear_buffers_before_each_transaction:
            self._print_debug(
                "Clearing serial buffers for port {}".format(self.serial.port)
            )
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

        if sys.version_info[0] > 2:
            request = bytes(
                request, encoding="latin1"
            )  # Convert types to make it Python3 compatible

        # Sleep to make sure 3.5 character times have passed
        minimum_silent_period = _calculate_minimum_silent_period(self.serial.baudrate)
        time_since_read = _now() - _latest_read_times.get(self.serial.port, 0)

        if time_since_read < minimum_silent_period:
            sleep_time = minimum_silent_period - time_since_read

            if self.debug:
                template = (
                    "Sleeping {:.2f} ms before sending. "
                    + "Minimum silent period: {:.2f} ms, time since read: {:.2f} ms."
                )
                text = template.format(
                    sleep_time * _SECONDS_TO_MILLISECONDS,
                    minimum_silent_period * _SECONDS_TO_MILLISECONDS,
                    time_since_read * _SECONDS_TO_MILLISECONDS,
                )
                self._print_debug(text)

            time.sleep(sleep_time)

        elif self.debug:
            template = (
                "No sleep required before write. "
                + "Time since previous read: {:.2f} ms, minimum silent period: {:.2f} ms."
            )
            text = template.format(
                time_since_read * _SECONDS_TO_MILLISECONDS,
                minimum_silent_period * _SECONDS_TO_MILLISECONDS,
            )
            self._print_debug(text)

        # Write request
        latest_write_time = _now()
        self.serial.write(request)

        # Read and discard local echo
        if self.handle_local_echo:
            local_echo_to_discard = self.serial.read(len(request))
            if self.debug:
                template = "Discarding this local echo: {!r} ({} bytes)."
                text = template.format(
                    local_echo_to_discard, len(local_echo_to_discard)
                )
                self._print_debug(text)
            if local_echo_to_discard != request:
                template = (
                    "Local echo handling is enabled, but the local echo does "
                    + "not match the sent request. "
                    + "Request: {!r} ({} bytes), local echo: {!r} ({} bytes)."
                )
                text = template.format(
                    request,
                    len(request),
                    local_echo_to_discard,
                    len(local_echo_to_discard),
                )
                raise LocalEchoError(text)

        # Read response
        answer = self.serial.read(number_of_bytes_to_read)
        _latest_read_times[self.serial.port] = _now()

        if self.close_port_after_each_call:
            self._print_debug("Closing port {}".format(self.serial.port))
            self.serial.close()

        if sys.version_info[0] > 2:
            # Convert types to make it Python3 compatible
            answer = str(answer, encoding="latin1")

        if self.debug:
            template = (
                "Response from instrument: {!r} ({}) ({} bytes), "
                + "roundtrip time: {:.1f} ms. Timeout for reading: {:.1f} ms.\n"
            )
            text = template.format(
                answer,
                _hexlify(answer),
                len(answer),
                (_latest_read_times.get(self.serial.port, 0) - latest_write_time)
                * _SECONDS_TO_MILLISECONDS,
                self.serial.timeout * _SECONDS_TO_MILLISECONDS,
            )
            self._print_debug(text)

        if not answer:
            raise NoResponseError("No communication with the instrument (no answer)")

        return answer








	# def calculateChecksum(self, command):
	# 	### calculates checksum for sending a command. Adds address and command bits.
	# 	# returns checksum <chksm> in hex representation of lowest byte

	# 	s = self.__address + command	#add hex strings to be used for calculating checksum
	# 	chksum = sum([int(s[2*i : (2*i)+2], 16) for i in range(int(len(s)/2))]) 	#add all bits as decimal values
	# 	chksum = hex(chksum % 256) #convert back to hex, only keep two bits
	# 	return codecs.encode(str.encode(chksum[-2:], 'hex_codec'))	#only consider the last bit for checksum