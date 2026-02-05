"""EtherCAT protocol engine implementation.

EtherCAT (Ethernet for Control Automation Technology) is a high-performance
real-time industrial Ethernet protocol developed by Beckhoff.

Key characteristics:
- Layer 2 protocol (EtherType 0x88A4)
- Processing on the fly: Sub-microsecond cycle times
- Daisy chain topology with ring redundancy option
- Distributed Clocks (DC) for synchronized outputs

Supported features:
- Master initialization and slave discovery
- State machine transitions (INIT → PREOP → SAFEOP → OP)
- Cyclic process data exchange (LRW)
- Mailbox communication (CoE/SDO)
- Distributed Clocks synchronization

Typical applications:
- Motion control (servo drives, stepper motors)
- CNC machines
- Packaging machines
- Robotics
"""

import random
from collections.abc import Iterator

from app.protocol_engines import register_engine
from app.protocol_engines.base import ProtocolEngine
from app.protocol_engines.ethercat.packets import (
    ALState,
    ESCRegister,
    EtherCATCommand,
    auto_increment_address,
    build_coe_sdo_upload_request,
    build_ethercat_datagram,
    build_ethercat_frame,
    build_fmmu_config,
    build_syncmanager_config,
    calculate_expected_wkc,
)
from app.protocol_engines.types import (
    EtherCATConversationState,
    FlowContext,
    PacketEvent,
    ProtocolType,
)


# Typical EtherCAT cycle times (microseconds)
CYCLE_TIMES_US = {
    "fast": 62.5,      # 62.5µs - High-speed servo
    "standard": 250,   # 250µs - Motion control
    "slow": 1000,      # 1ms - General I/O
    "default": 1000,
}


@register_engine(ProtocolType.ETHERCAT)
class EtherCATEngine(ProtocolEngine):
    """EtherCAT protocol engine.

    Generates realistic EtherCAT traffic patterns including:
    - Network scanning and slave discovery
    - State machine transitions
    - Cyclic process data exchange
    - Mailbox/SDO communication
    """

    @property
    def protocol_type(self) -> ProtocolType:
        return ProtocolType.ETHERCAT

    def create_initial_state(self, flow: FlowContext) -> EtherCATConversationState:
        """Create initial conversation state for EtherCAT."""
        num_slaves = flow.config.get("num_slaves", 4)
        cycle_mode = flow.config.get("cycle_mode", "standard")

        return EtherCATConversationState(
            flow_id=flow.flow_id,
            state_name="idle",
            datagram_idx=random.randint(0, 255),
            num_slaves=num_slaves,
            al_state=ALState.INIT,
            dc_enabled=flow.config.get("dc_enabled", True),
        )

    def generate_startup_sequence(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate EtherCAT master initialization sequence.

        This includes:
        1. Network scan (broadcast read of AL Status)
        2. Slave discovery (auto-increment reads)
        3. Station address assignment
        4. SyncManager configuration
        5. FMMU configuration
        6. State machine transitions to OP
        7. Distributed Clocks initialization (if enabled)
        """
        current_time = start_time_ms
        num_slaves = state.num_slaves
        src_mac = flow.source.mac_address

        # Phase 1: Broadcast read to discover slaves
        # BRD command to AL Status register
        yield from self._generate_broadcast_scan(flow, state, current_time)
        current_time += 0.5  # 500µs for processing

        # Phase 2: Auto-increment scan to identify each slave
        yield from self._generate_slave_scan(flow, state, current_time)
        current_time += num_slaves * 0.2  # 200µs per slave

        # Phase 3: Assign station addresses
        yield from self._generate_address_assignment(flow, state, current_time)
        current_time += num_slaves * 0.3  # 300µs per slave

        # Phase 4: Configure SyncManagers for mailbox
        yield from self._generate_syncmanager_config(flow, state, current_time)
        current_time += num_slaves * 0.5  # 500µs per slave

        # Phase 5: Transition to PRE-OP
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.PREOP
        )
        current_time += 2.0  # 2ms for state transition

        # Phase 6: Configure FMMUs for process data
        yield from self._generate_fmmu_config(flow, state, current_time)
        current_time += num_slaves * 0.5

        # Phase 7: Configure SyncManagers for process data
        yield from self._generate_process_data_sm_config(flow, state, current_time)
        current_time += num_slaves * 0.3

        # Phase 8: Distributed Clocks initialization
        if state.dc_enabled:
            yield from self._generate_dc_initialization(flow, state, current_time)
            current_time += num_slaves * 1.0  # 1ms per slave for DC

        # Phase 9: Transition to SAFE-OP
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.SAFEOP
        )
        current_time += 5.0  # 5ms for SAFE-OP transition

        # Phase 10: Start cyclic data and transition to OP
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.OP
        )

        # Update state to OP
        state.transition_state(ALState.OP)

    def _generate_broadcast_scan(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate broadcast read to discover slaves."""
        # BRD command to read AL Status from all slaves
        datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.BRD,
            idx=state.next_idx(),
            adp=0x0000,  # Ignored for broadcast
            ado=ESCRegister.AL_STATUS,
            data=bytes(2),  # 2 bytes to read
        )

        frame = build_ethercat_frame(
            datagrams=[datagram],
            src_mac=flow.source.mac_address,
        )

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=frame,
            direction="request",
            metadata={
                "type": "ethercat_broadcast_scan",
                "command": "BRD",
                "register": "AL_STATUS",
            },
        )

        # Response comes back with all slaves' data
        response_datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.BRD,
            idx=state.datagram_idx - 1,
            adp=0x0000,
            ado=ESCRegister.AL_STATUS,
            data=bytes([ALState.INIT, 0x00]),  # All slaves in INIT
            wkc=state.num_slaves,
        )

        response_frame = build_ethercat_frame(
            datagrams=[response_datagram],
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
        )

        yield PacketEvent(
            timestamp_ms=time_ms + 0.1,  # 100µs round-trip
            flow_id=flow.flow_id,
            packet_bytes=response_frame,
            direction="response",
            metadata={
                "type": "ethercat_broadcast_response",
                "wkc": state.num_slaves,
                "slaves_found": state.num_slaves,
            },
        )

    def _generate_slave_scan(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate auto-increment scan to identify each slave."""
        current_time = time_ms

        for position in range(state.num_slaves):
            adp = auto_increment_address(position)

            # APRD to read device type
            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.APRD,
                idx=state.next_idx(),
                adp=adp,
                ado=ESCRegister.TYPE,
                data=bytes(2),  # Type + Revision
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_slave_scan",
                    "command": "APRD",
                    "position": position,
                    "adp": hex(adp),
                },
            )

            # Simulated response with device info
            device_type = random.choice([0x00, 0x01, 0x02, 0x05])  # Various ESC types
            revision = random.randint(1, 10)

            response_datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.APRD,
                idx=state.datagram_idx - 1,
                adp=adp,
                ado=ESCRegister.TYPE,
                data=bytes([device_type, revision]),
                wkc=1,
            )

            response_frame = build_ethercat_frame(
                datagrams=[response_datagram],
                src_mac=flow.destination.mac_address,
                dst_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time + 0.05,
                flow_id=flow.flow_id,
                packet_bytes=response_frame,
                direction="response",
                metadata={
                    "type": "ethercat_slave_info",
                    "position": position,
                    "device_type": device_type,
                    "revision": revision,
                },
            )

            current_time += 0.1

    def _generate_address_assignment(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate station address assignment for each slave."""
        current_time = time_ms
        base_station_addr = flow.config.get("base_station_addr", 0x1001)

        for position in range(state.num_slaves):
            adp = auto_increment_address(position)
            station_addr = base_station_addr + position

            # APWR to write station address
            addr_data = station_addr.to_bytes(2, "little")
            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.APWR,
                idx=state.next_idx(),
                adp=adp,
                ado=ESCRegister.STATION_ADDR,
                data=addr_data,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_address_assign",
                    "command": "APWR",
                    "position": position,
                    "station_addr": hex(station_addr),
                },
            )

            # Store station address in state
            state.station_addresses.append(station_addr)
            state.slave_states[station_addr] = ALState.INIT

            # Response
            response_datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.APWR,
                idx=state.datagram_idx - 1,
                adp=adp,
                ado=ESCRegister.STATION_ADDR,
                data=addr_data,
                wkc=1,
            )

            response_frame = build_ethercat_frame(
                datagrams=[response_datagram],
                src_mac=flow.destination.mac_address,
                dst_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time + 0.05,
                flow_id=flow.flow_id,
                packet_bytes=response_frame,
                direction="response",
                metadata={
                    "type": "ethercat_address_assigned",
                    "station_addr": hex(station_addr),
                    "wkc": 1,
                },
            )

            current_time += 0.15

    def _generate_syncmanager_config(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SyncManager 0/1 configuration for mailbox."""
        current_time = time_ms

        for station_addr in state.station_addresses:
            # SM0: Mailbox Out (Master -> Slave)
            sm0_config = build_syncmanager_config(
                physical_start=0x1000,
                length=128,
                control=0x26,  # Mailbox mode, write, PDI interrupt
                activate=0x01,
            )

            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.SM_0,
                data=sm0_config,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_sm_config",
                    "command": "FPWR",
                    "station_addr": hex(station_addr),
                    "syncmanager": 0,
                },
            )

            current_time += 0.2

            # SM1: Mailbox In (Slave -> Master)
            sm1_config = build_syncmanager_config(
                physical_start=0x1080,
                length=128,
                control=0x22,  # Mailbox mode, read, PDI interrupt
                activate=0x01,
            )

            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.SM_1,
                data=sm1_config,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_sm_config",
                    "station_addr": hex(station_addr),
                    "syncmanager": 1,
                },
            )

            current_time += 0.2

    def _generate_state_transition(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
        target_state: int,
    ) -> Iterator[PacketEvent]:
        """Generate state machine transition for all slaves."""
        # Write AL Control to all slaves via broadcast
        state_data = target_state.to_bytes(2, "little")

        datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.BWR,
            idx=state.next_idx(),
            adp=0x0000,
            ado=ESCRegister.AL_CONTROL,
            data=state_data,
        )

        frame = build_ethercat_frame(
            datagrams=[datagram],
            src_mac=flow.source.mac_address,
        )

        state_names = {
            ALState.INIT: "INIT",
            ALState.PREOP: "PRE-OP",
            ALState.SAFEOP: "SAFE-OP",
            ALState.OP: "OP",
        }

        yield PacketEvent(
            timestamp_ms=time_ms,
            flow_id=flow.flow_id,
            packet_bytes=frame,
            direction="request",
            metadata={
                "type": "ethercat_state_transition",
                "command": "BWR",
                "target_state": state_names.get(target_state, hex(target_state)),
            },
        )

        # Update state tracking
        for addr in state.station_addresses:
            state.slave_states[addr] = target_state

        # Read back AL Status to confirm
        read_datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.BRD,
            idx=state.next_idx(),
            adp=0x0000,
            ado=ESCRegister.AL_STATUS,
            data=bytes(2),
        )

        read_frame = build_ethercat_frame(
            datagrams=[read_datagram],
            src_mac=flow.source.mac_address,
        )

        yield PacketEvent(
            timestamp_ms=time_ms + 1.0,
            flow_id=flow.flow_id,
            packet_bytes=read_frame,
            direction="request",
            metadata={
                "type": "ethercat_state_verify",
                "command": "BRD",
            },
        )

        # Response confirming state
        response_datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.BRD,
            idx=state.datagram_idx - 1,
            adp=0x0000,
            ado=ESCRegister.AL_STATUS,
            data=target_state.to_bytes(2, "little"),
            wkc=state.num_slaves,
        )

        response_frame = build_ethercat_frame(
            datagrams=[response_datagram],
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
        )

        yield PacketEvent(
            timestamp_ms=time_ms + 1.1,
            flow_id=flow.flow_id,
            packet_bytes=response_frame,
            direction="response",
            metadata={
                "type": "ethercat_state_confirmed",
                "state": state_names.get(target_state, hex(target_state)),
                "wkc": state.num_slaves,
            },
        )

    def _generate_fmmu_config(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate FMMU configuration for process data mapping."""
        current_time = time_ms
        logical_addr = flow.config.get("logical_start_addr", 0x00000000)
        bytes_per_slave = flow.config.get("bytes_per_slave", 8)

        for idx, station_addr in enumerate(state.station_addresses):
            slave_logical_addr = logical_addr + (idx * bytes_per_slave)

            # FMMU for outputs (LWR mapping)
            fmmu_out = build_fmmu_config(
                logical_start=slave_logical_addr,
                length=bytes_per_slave // 2,
                physical_start=0x1100,  # Process data output area
                read_enable=False,
                write_enable=True,
            )

            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.FMMU_0,
                data=fmmu_out,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_fmmu_config",
                    "station_addr": hex(station_addr),
                    "fmmu": 0,
                    "logical_addr": hex(slave_logical_addr),
                },
            )

            current_time += 0.2

        state.logical_address = logical_addr

    def _generate_process_data_sm_config(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate SyncManager 2/3 configuration for process data."""
        current_time = time_ms
        bytes_per_slave = flow.config.get("bytes_per_slave", 8)

        for station_addr in state.station_addresses:
            # SM2: Process data outputs
            sm2_config = build_syncmanager_config(
                physical_start=0x1100,
                length=bytes_per_slave // 2,
                control=0x64,  # Buffered 3-buffer mode, write
                activate=0x01,
            )

            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.SM_2,
                data=sm2_config,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_sm_config",
                    "station_addr": hex(station_addr),
                    "syncmanager": 2,
                },
            )

            current_time += 0.15

    def _generate_dc_initialization(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate Distributed Clocks initialization sequence."""
        current_time = time_ms
        cycle_time_ns = flow.config.get("cycle_time_ns", 1000000)  # 1ms default

        for station_addr in state.station_addresses:
            # Read DC receive time for delay calculation (FRMW)
            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FRMW,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.DC_RECV_TIME_P0,
                data=bytes(8),
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_dc_delay_read",
                    "station_addr": hex(station_addr),
                },
            )

            current_time += 0.2

            # Write SYNC0 cycle time
            cycle_data = cycle_time_ns.to_bytes(4, "little")
            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.SYNC0_CYCLE_TIME,
                data=cycle_data,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_dc_sync0_config",
                    "station_addr": hex(station_addr),
                    "cycle_time_ns": cycle_time_ns,
                },
            )

            current_time += 0.2

            # Activate DC
            dc_activate = 0x0300.to_bytes(2, "little")  # SYNC0 enabled
            datagram = build_ethercat_datagram(
                cmd=EtherCATCommand.FPWR,
                idx=state.next_idx(),
                adp=station_addr,
                ado=ESCRegister.DC_ACTIVATION,
                data=dc_activate,
            )

            frame = build_ethercat_frame(
                datagrams=[datagram],
                src_mac=flow.source.mac_address,
            )

            yield PacketEvent(
                timestamp_ms=current_time,
                flow_id=flow.flow_id,
                packet_bytes=frame,
                direction="request",
                metadata={
                    "type": "ethercat_dc_activate",
                    "station_addr": hex(station_addr),
                },
            )

            current_time += 0.3

    def generate_poll_cycle(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        cycle_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate cyclic EtherCAT process data exchange.

        Uses LRW (Logical Read/Write) command for efficient
        bidirectional process data exchange in a single frame.
        """
        if state.al_state != ALState.OP:
            # Not in OP state - no cyclic data
            return

        bytes_per_slave = flow.config.get("bytes_per_slave", 8)
        total_data_size = state.num_slaves * bytes_per_slave

        # Generate output data (simulated control values)
        output_data = self._generate_process_data(state, bytes_per_slave)

        # Build LRW datagram
        datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.LRW,
            idx=state.next_idx(),
            adp=(state.logical_address >> 16) & 0xFFFF,
            ado=state.logical_address & 0xFFFF,
            data=output_data,
        )

        frame = build_ethercat_frame(
            datagrams=[datagram],
            src_mac=flow.source.mac_address,
        )

        yield PacketEvent(
            timestamp_ms=cycle_time_ms,
            flow_id=flow.flow_id,
            packet_bytes=frame,
            direction="request",
            metadata={
                "type": "ethercat_cyclic_lrw",
                "command": "LRW",
                "cycle": state.cycle_counter,
                "logical_addr": hex(state.logical_address),
                "data_size": len(output_data),
            },
        )

        # Response with input data
        input_data = self._generate_process_data(state, bytes_per_slave)

        response_datagram = build_ethercat_datagram(
            cmd=EtherCATCommand.LRW,
            idx=state.datagram_idx - 1,
            adp=(state.logical_address >> 16) & 0xFFFF,
            ado=state.logical_address & 0xFFFF,
            data=input_data,
            wkc=state.num_slaves * 3,  # LRW WKC = 3 per slave
        )

        response_frame = build_ethercat_frame(
            datagrams=[response_datagram],
            src_mac=flow.destination.mac_address,
            dst_mac=flow.source.mac_address,
        )

        # Get response timing
        applicator = flow.destination.fingerprint_applicator
        timing_sample = applicator.get_response_delay()
        response_time = cycle_time_ms + min(timing_sample.delay_ms, 0.5)  # Max 500µs

        yield PacketEvent(
            timestamp_ms=response_time,
            flow_id=flow.flow_id,
            packet_bytes=response_frame,
            direction="response",
            metadata={
                "type": "ethercat_cyclic_response",
                "cycle": state.cycle_counter,
                "wkc": state.num_slaves * 3,
                "expected_wkc": state.num_slaves * 3,
            },
        )

        state.increment_cycle()

    def _generate_process_data(
        self,
        state: EtherCATConversationState,
        bytes_per_slave: int,
    ) -> bytes:
        """Generate simulated process data for cyclic exchange."""
        data = bytearray()

        for _ in range(state.num_slaves):
            # Simulated process data with varying values
            for i in range(bytes_per_slave):
                value = (state.cycle_counter + i) & 0xFF
                data.append(value)

        return bytes(data)

    def generate_shutdown_sequence(
        self,
        flow: FlowContext,
        state: EtherCATConversationState,
        start_time_ms: float,
    ) -> Iterator[PacketEvent]:
        """Generate EtherCAT shutdown sequence.

        Transitions slaves back through SAFE-OP → PRE-OP → INIT.
        """
        current_time = start_time_ms

        # Transition to SAFE-OP
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.SAFEOP
        )
        current_time += 5.0

        # Transition to PRE-OP
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.PREOP
        )
        current_time += 2.0

        # Transition to INIT
        yield from self._generate_state_transition(
            flow, state, current_time, ALState.INIT
        )

        state.transition_state(ALState.INIT)

    def validate_config(self, config: dict) -> list[str]:
        """Validate EtherCAT configuration."""
        errors = []

        # Validate number of slaves
        num_slaves = config.get("num_slaves", 4)
        if num_slaves < 1 or num_slaves > 65535:
            errors.append("num_slaves must be between 1 and 65535")

        # Validate cycle time
        cycle_time_ns = config.get("cycle_time_ns", 1000000)
        if cycle_time_ns < 31250:  # 31.25µs minimum
            errors.append("cycle_time_ns must be at least 31250 (31.25µs)")

        # Validate bytes per slave
        bytes_per_slave = config.get("bytes_per_slave", 8)
        if bytes_per_slave < 1 or bytes_per_slave > 1486:
            errors.append("bytes_per_slave must be between 1 and 1486")

        return errors
