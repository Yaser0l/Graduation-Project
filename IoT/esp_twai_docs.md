# Two-Wire Automotive Interface (TWAI)

This document introduces the features of the Two-Wire Automotive Interface (TWAI) controller driver in ESP-IDF. The chapter structure is as follows:

## Overview

TWAI is a highly reliable, multi-master, real-time, serial asynchronous communication protocol designed for automotive and industrial applications. It is compatible with the frame structure defined in the ISO 11898-1 standard and supports both standard frames with 11-bit identifiers and extended frames with 29-bit identifiers. The protocol supports message prioritization with lossless arbitration, automatic retransmission, and fault confinement mechanisms. The ESP32-S3 includes 1 TWAI controllers, allowing for the creation of 1 driver instances.

The TWAI controllers on the ESP32-S3 are **not compatible with FD format frames and will interpret such frames as errors.**

Thanks to its hardware-based fault tolerance and multi-master architecture, the TWAI driver is ideal for scenarios such as:

- Serving as a robust communication bus in environments with significant electrical noise

- Enabling long-distance communication across multiple sensors/actuators with resilience to single-node failures

- Building decentralized distributed local networks that avoid the unpredictability of single-master designs

- Acting as a bridging node alongside other communication protocols

## Getting Started

This section provides a quick overview of how to use the TWAI driver. Through simple examples, it demonstrates how to create a TWAI node instance, transmit and receive messages on the bus, and safely stop and uninstall the driver. The general usage flow is as follows:

![](../../_images/base_flow.drawio.svg){.align-center}

### Hardware Connection

The ESP32-S3 does not integrate an internal TWAI transceiver. Therefore, an external transceiver is required to connect to a TWAI bus. The model of the external transceiver depends on the physical layer standard used in your specific application. For example, a TJA105x transceiver can be used to comply with the ISO 11898-2 standard.

![ESP32 to Transceiver Wiring](../../_images/hw_connection.svg){.align-center}

Specifically:

- For single-node testing, you can directly short the TX and RX pins to omit the transceiver.

- BUS_OFF (optional): Outputs a low logic level (0 V) when the TWAI controller enters the bus-off state. Otherwise, it remains at a high logic level (3.3 V).

- CLK_OUT (optional): Outputs the time quantum clock of the controller, which is a divided version of the source clock.

### Creating and Starting a TWAI Node

First, we need to create a TWAI instance. The following code demonstrates how to create a TWAI node with a baud rate of 200 kHz:

```{#codecell0}
#include "esp_twai.h"
#include "esp_twai_onchip.h"

twai_node_handle_t node_hdl = NULL;
twai_onchip_node_config_t node_config = {
    .io_cfg.tx = 4,             // TWAI TX GPIO pin
    .io_cfg.rx = 5,             // TWAI RX GPIO pin
    .bit_timing.bitrate = 200000,  // 200 kbps bitrate
    .tx_queue_depth = 5,        // Transmit queue depth set to 5
};
// Create a new TWAI controller driver instance
ESP_ERROR_CHECK(twai_new_node_onchip(&node_config, &node_hdl));
// Start the TWAI controller
ESP_ERROR_CHECK(twai_node_enable(node_hdl));
```

When creating a TWAI instance, you must configure parameters such as GPIO pins and baud rate using the [`twai_onchip_node_config_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv425twai_onchip_node_config_t "twai_onchip_node_config_t"){.reference .internal} structure. These parameters determine how the TWAI node operates. Then, you can call the [`twai_new_node_onchip()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv420twai_new_node_onchipPK25twai_onchip_node_config_tP18twai_node_handle_t "twai_new_node_onchip"){.reference .internal} function to create a new TWAI instance. This function returns a handle to the newly created instance. A TWAI handle is essentially a pointer to an internal TWAI memory object of type [`twai_node_handle_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal}.

Below are additional configuration fields of the [`twai_onchip_node_config_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv425twai_onchip_node_config_t "twai_onchip_node_config_t"){.reference .internal} structure along with their descriptions:

- [`twai_onchip_node_config_t::clk_src`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t7clk_srcE "twai_onchip_node_config_t::clk_src"){.reference .internal}: Specifies the clock source used by the controller. Supported sources are listed in [`twai_clock_source_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv419twai_clock_source_t "twai_clock_source_t"){.reference .internal}.

- `twai_onchip_node_config_t::bit_timing::sp_permill`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Specifies the location of the sample point. ssp_permill sets the location of the secondary sample point and can be used to fine-tune timing in low SNR conditions.

- [`twai_onchip_node_config_t::data_timing`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t11data_timingE "twai_onchip_node_config_t::data_timing"){.reference .internal}: Specifies the baud rate and sample point for the data phase in FD frames. This field is ignored if the controller does not support FD format.

- [`twai_onchip_node_config_t::fail_retry_cnt`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t14fail_retry_cntE "twai_onchip_node_config_t::fail_retry_cnt"){.reference .internal}: Sets the number of retry attempts on transmission failure. -1 indicates infinite retries until success or bus-off; 0 disables retries (single-shot mode); 1 retries once, and so on.

- [`twai_onchip_node_config_t::intr_priority`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t13intr_priorityE "twai_onchip_node_config_t::intr_priority"){.reference .internal}: Interrupt priority in the range \[0:3\], where higher values indicate higher priority.

- [`twai_onchip_node_config_t::flags`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t5flagsE "twai_onchip_node_config_t::flags"){.reference .internal}: A set of flags for fine-tuning driver behavior. Options include:

  > - `twai_onchip_node_config_t::flags::enable_self_test`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Enables self-test mode. In this mode, ACK is not checked during transmission, which is useful for single-node testing.
  > - `twai_onchip_node_config_t::flags::enable_loopback`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Enables loopback mode. The node will receive its own transmitted messages (subject to filter configuration), while also transmitting them to the bus.
  > - `twai_onchip_node_config_t::flags::enable_listen_only`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Configures the node in listen-only mode. In this mode, the node only receives and does not transmit any dominant bits, including ACK and error frames.
  > - `twai_onchip_node_config_t::flags::no_receive_rtr`{.xref .cpp .cpp-member .docutils .literal .notranslate}: When using filters, determines whether remote frames matching the ID pattern should be filtered out.

The [`twai_node_enable()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv416twai_node_enable18twai_node_handle_t "twai_node_enable"){.reference .internal} function starts the TWAI controller. Once enabled, the controller is connected to the bus and can transmit messages. It also generates events upon receiving messages from other nodes on the bus or when bus errors are detected.

The corresponding function, [`twai_node_disable()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv417twai_node_disable18twai_node_handle_t "twai_node_disable"){.reference .internal}, immediately stops the node and disconnects it from the bus. Any ongoing transmissions will be aborted. When the node is re-enabled later, if there are pending transmissions in the queue, the driver will immediately initiate a new transmission attempt.

### Transmitting Messages

TWAI messages come in various types, which are specified by their headers. A typical data frame consists primarily of a header and data payload, with a structure similar to the following:

![](../../_images/frame_struct.svg){.align-center}

To reduce performance overhead caused by memory copying, the TWAI driver uses pointers to pass messages. The driver is designed to operate in asynchronous mode, so the [`twai_frame_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv412twai_frame_t "twai_frame_t"){.reference .internal} structure and the memory pointed to by [`twai_frame_t::buffer`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N12twai_frame_t6bufferE "twai_frame_t::buffer"){.reference .internal} must remain valid until the transmission is actually complete. You can determine when transmission is complete in the following ways:

- Call the [`twai_node_transmit_wait_all_done()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv432twai_node_transmit_wait_all_done18twai_node_handle_ti "twai_node_transmit_wait_all_done"){.reference .internal} function to wait for all transmissions to complete.

- Register the [`twai_event_callbacks_t::on_tx_done`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N22twai_event_callbacks_t10on_tx_doneE "twai_event_callbacks_t::on_tx_done"){.reference .internal} event callback function to receive a notification when transmission is complete.

The following code demonstrates how to transmit a typical data frame:

```{#codecell1}
uint8_t send_buff[8] = {0};
twai_frame_t tx_msg = {
    .header.id = 0x1,           // Message ID
    .header.ide = true,         // Use 29-bit extended ID format
    .buffer = send_buff,        // Pointer to data to transmit
    .buffer_len = sizeof(send_buff),  // Length of data to transmit
};
ESP_ERROR_CHECK(twai_node_transmit(node_hdl, &tx_msg, 0));  // Timeout = 0: returns immediately if queue is full
ESP_ERROR_CHECK(twai_node_transmit_wait_all_done(node_hdl, -1));  // Wait for transmission to finish
```

In this example, `twai_frame_t::header::id`{.xref .cpp .cpp-member .docutils .literal .notranslate} specifies the ID of the message as 0x01. Message IDs are typically used to indicate the type of message in an application and also play a role in bus arbitration during transmission---lower values indicate higher priority on the bus. [`twai_frame_t::buffer`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N12twai_frame_t6bufferE "twai_frame_t::buffer"){.reference .internal} points to the memory address where the data to be transmitted is stored, and [`twai_frame_t::buffer_len`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N12twai_frame_t10buffer_lenE "twai_frame_t::buffer_len"){.reference .internal} specifies the length of that data. The [`twai_node_transmit()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv418twai_node_transmit18twai_node_handle_tPK12twai_frame_ti "twai_node_transmit"){.reference .internal} function is thread-safe and can also be called from an ISR. When called from an ISR, the `timeout`{.docutils .literal .notranslate} parameter is ignored, and the function will not block.

Note that `twai_frame_t::header::dlc`{.xref .cpp .cpp-member .docutils .literal .notranslate} can also specify the length of the data in the frame. The DLC (Data Length Code) is mapped to the actual data length as defined in ISO 11898-1. You can use either [`twaifd_dlc2len()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv414twaifd_dlc2len8uint16_t "twaifd_dlc2len"){.reference .internal} or [`twaifd_len2dlc()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv414twaifd_len2dlc8uint16_t "twaifd_len2dlc"){.reference .internal} for conversion. If both dlc and buffer_len are non-zero, they must represent the same length.

The [`twai_frame_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv412twai_frame_t "twai_frame_t"){.reference .internal} message structure also includes other configuration fields:

- `twai_frame_t::dlc`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Data Length Code. For classic frames, values \[0:8\] represent lengths \[0:8\]; for FD format, values \[0:15\] represent lengths up to 64 bytes.

- `twai_frame_t::header::ide`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Indicates use of a 29-bit extended ID format.

- `twai_frame_t::header::rtr`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Indicates the frame is a remote frame, which contains no data payload.

- `twai_frame_t::header::fdf`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Marks the frame as an FD format frame, supporting up to 64 bytes of data.

- `twai_frame_t::header::brs`{.xref .cpp .cpp-member .docutils .literal .notranslate}: Enables use of a separate data-phase baud rate when transmitting.

- `twai_frame_t::header::esi`{.xref .cpp .cpp-member .docutils .literal .notranslate}: For received frames, indicates the error state of the transmitting node.

### Receiving Messages

Receiving messages must be done within a receive event callback. Therefore, to receive messages, you need to register a receive event callback via [`twai_event_callbacks_t::on_rx_done`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N22twai_event_callbacks_t10on_rx_doneE "twai_event_callbacks_t::on_rx_done"){.reference .internal} before starting the controller. This enables the controller to deliver received messages via the callback when events occur. The following code snippets demonstrate how to register the receive event callback and how to handle message reception inside the callback:

Registering the receive event callback (before starting the controller):

```{#codecell2}
twai_event_callbacks_t user_cbs = {
    .on_rx_done = twai_rx_cb,
};
ESP_ERROR_CHECK(twai_node_register_event_callbacks(node_hdl, &user_cbs, NULL));
```

Receiving messages inside the callback:

```{#codecell3}
static bool twai_rx_cb(twai_node_handle_t handle, const twai_rx_done_event_data_t *edata, void *user_ctx)
{
    uint8_t recv_buff[8];
    twai_frame_t rx_frame = {
        .buffer = recv_buff,
        .buffer_len = sizeof(recv_buff),
    };
    if (ESP_OK == twai_node_receive_from_isr(handle, &rx_frame)) {
        // receive ok, do something here
    }
    return false;
}
```

Similarly, since the driver uses pointers for message passing, you must configure the pointer [`twai_frame_t::buffer`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N12twai_frame_t6bufferE "twai_frame_t::buffer"){.reference .internal} and its memory length [`twai_frame_t::buffer_len`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N12twai_frame_t10buffer_lenE "twai_frame_t::buffer_len"){.reference .internal} before receiving.

### Frame Timestamp

The TWAI driver supports creating a 64-bit timestamp for each successfully received frame, enabling this feature by configuring the [`twai_onchip_node_config_t::timestamp_resolution_hz`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t23timestamp_resolution_hzE "twai_onchip_node_config_t::timestamp_resolution_hz"){.reference .internal} field when creating the node. The timestamp is stored in the `twai_frame_t::header::timestamp`{.xref .cpp .cpp-member .docutils .literal .notranslate} field of the received frame.

The node time inherits from the system time, i.e. the time starts from the power-on of the chip, and is not affected by the stop/restart/BUS_OFF state during the node\'s lifetime.

### Stopping and Deleting the Node

When the TWAI node is no longer needed, you should call [`twai_node_delete()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv416twai_node_delete18twai_node_handle_t "twai_node_delete"){.reference .internal} to release software and hardware resources. Make sure the TWAI controller is stopped before deleting the node.

## Advanced Features

After understanding the basic usage, you can further explore more advanced capabilities of the TWAI driver. The driver supports more detailed controller configuration and error feedback features. The complete driver feature diagram is shown below:

![](../../_images/full_flow.drawio.svg){.align-center}

### Transmit from ISR

The TWAI driver supports transmitting messages from an Interrupt Service Routine (ISR). This is particularly useful for applications requiring low-latency responses or periodic transmissions triggered by hardware timers. For example, you can trigger a new transmission from within the `on_tx_done`{.docutils .literal .notranslate} callback, which is executed in an ISR context.

```{#codecell4}
static bool twai_tx_done_cb(twai_node_handle_t handle, const twai_tx_done_event_data_t *edata, void *user_ctx)
{
    // A frame has been successfully transmitted. Queue another one.
    // The frame and its data buffer must be valid until transmission is complete.
    static const uint8_t data_buffer[] = {1, 2, 3, 4};
    static const twai_frame_t tx_frame = {
        .header.id = 0x2,
        .buffer = (uint8_t *)data_buffer,
        .buffer_len = sizeof(data_buffer),
    };

    // The `twai_node_transmit` is safe to be called in an ISR context
    twai_node_transmit(handle, &tx_frame, 0);
    return false;
}
```

Note

When calling [`twai_node_transmit()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv418twai_node_transmit18twai_node_handle_tPK12twai_frame_ti "twai_node_transmit"){.reference .internal} from an ISR, the `timeout`{.docutils .literal .notranslate} parameter is ignored, and the function will not block. If the transmit queue is full, the function will return immediately with an error. It is the application\'s responsibility to handle cases where the queue is full. Similarly, the `twai_frame_t`{.docutils .literal .notranslate} structure and the memory pointed to by `buffer`{.docutils .literal .notranslate} must remain valid until the transmission is complete. You can get the completed frame by the [`twai_tx_done_event_data_t::done_tx_frame`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_tx_done_event_data_t13done_tx_frameE "twai_tx_done_event_data_t::done_tx_frame"){.reference .internal} pointer.

### Bit Timing Customization

Unlike other asynchronous communication protocols, the TWAI controller performs counting and sampling within one bit time in units of **Time Quanta (Tq)**. The number of time quanta per bit determines the final baud rate and the sample point position. When signal quality is poor, you can manually fine-tune these timing segments to meet specific requirements. The time quanta within a bit time are divided into different segments, as illustrated below:

![Bit timing configuration](../../_images/bit_timing.svg){.align-center}

The synchronization segment (sync) is fixed at 1 Tq. The sample point lies between time segments tseg1 and tseg2. The Synchronization Jump Width (SJW) defines the maximum number of time quanta by which a bit time can be lengthened or shortened for synchronization purposes, ranging from \[1 : tseg2\]. The clock source divided by the baud rate prescaler (BRP) equals the time quantum. The total sum of all segments equals one bit time. Therefore, the following formula applies:

- Baud rate (bitrate):

$$\text{bitrate} = \frac{f_{\text{src}}}{\text{brp} \cdot (1 + \text{prop\_seg} + \text{tseg}_{1} + \text{tseg}_{2})}$$

- Sample point:

$$\text{sample\_point} = \frac{1 + \text{prop\_seg} + \text{tseg}_{1}}{1 + \text{prop\_seg} + \text{tseg}_{1} + \text{tseg}_{2}}$$

The following code demonstrates how to configure a baud rate of 500 Kbit/s with a sample point at 75% when using an 80 MHz clock source:

```{#codecell5}
twai_timing_advanced_config_t timing_cfg = {
    .brp = 8,       // Prescaler set to 8, time quantum = 80M / 8 = 10 MHz (10M Tq)
    .prop_seg = 10, // Propagation segment
    .tseg_1 = 4,    // Phase segment 1
    .tseg_2 = 5,    // Phase segment 2
    .sjw = 3,       // Synchronization Jump Width
};
ESP_ERROR_CHECK(twai_node_reconfig_timing(node_hdl, &timing_cfg, NULL)); // Configure arbitration phase timing; NULL means FD data phase timing is not configured
```

When manually configuring these timing segments, it is important to pay attention to the supported range of each segment according to the specific hardware. The timing configuration function [`twai_node_reconfig_timing()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv425twai_node_reconfig_timing18twai_node_handle_tPK29twai_timing_advanced_config_tPK29twai_timing_advanced_config_t "twai_node_reconfig_timing"){.reference .internal} can configure the timing parameters for both the arbitration phase and the FD data phase either simultaneously or separately. When the controller does not support FD format, the data phase configuration is ignored. The timing parameter struct [`twai_timing_advanced_config_t`{.xref .cpp .cpp-type .docutils .literal .notranslate}](#_CPPv429twai_timing_advanced_config_t "twai_timing_advanced_config_t"){.reference .internal} also includes the following additional configuration fields:

- `twai_timing_advanced_config_t::clk_src`{.xref .cpp .cpp-member .docutils .literal .notranslate} --- The clock source.

- [`twai_timing_advanced_config_t::ssp_offset`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N29twai_timing_advanced_config_t10ssp_offsetE "twai_timing_advanced_config_t::ssp_offset"){.reference .internal} --- The number of time quanta by which the secondary sample point (SSP) is offset relative to the synchronization segment.

Note

Different combinations of `brp`{.docutils .literal .notranslate}, `prop_seg`{.docutils .literal .notranslate}, `tseg_1`{.docutils .literal .notranslate}, `tseg_2`{.docutils .literal .notranslate}, and `sjw`{.docutils .literal .notranslate} can achieve the same baud rate. Users should consider factors such as **propagation delay, node processing time, and phase errors**, and adjust the timing parameters based on the physical characteristics of the bus.

### Filter Configuration

#### Mask Filters

The TWAI controller hardware can filter messages based on their ID to reduce software and hardware overhead, thereby improving node efficiency. Nodes that filter out certain messages will **not receive those messages, but will still send acknowledgments (ACKs)**.

ESP32-S3 includes 1 mask filters. A message passing through any one of these filters will be received by the node. A typical TWAI mask filter is configured with an ID and a MASK, where:

- ID: represents the expected message ID, either the standard 11-bit or extended 29-bit format.

- MASK: defines the filtering rules for each bit of the ID:

  > - \'0\' means the corresponding bit is ignored (any value passes).
  > - \'1\' means the corresponding bit must match exactly to pass.
  > - When both ID and MASK are 0, the filter ignores all bits and accepts all frames.
  > - When both ID and MASK are set to the maximum 0xFFFFFFFF, the filter accepts no frames.

The following code demonstrates how to calculate the MASK and configure a filter:

```{#codecell6}
twai_mask_filter_config_t mfilter_cfg = {
    .id = 0x10,         // 0b 000 0001 0000
    .mask = 0x7f0,      // 0b 111 1111 0000 — the upper 7 bits must match strictly, the lower 4 bits are ignored, accepts IDs of the form
                        // 0b 000 0001 xxxx (hex 0x01x)
    .is_ext = false,    // Accept only standard IDs, not extended IDs
};
ESP_ERROR_CHECK(twai_node_config_mask_filter(node_hdl, 0, &mfilter_cfg));   // Configure on filter 0
```

#### Dual Filter Mode

ESP32-S3 supports dual filter mode, which allows the hardware to be configured as two parallel independent 16-bit mask filters. By enabling this, more IDs can be received. Note that using dual filter mode to filter 29-bit extended IDs, each filter can only filter the upper 16 bits of the ID, while the remaining 13 bits are not filtered. The following code demonstrates how to configure dual filter mode using the function [`twai_make_dual_filter()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv421twai_make_dual_filter8uint32_t8uint32_t8uint32_t8uint32_tb "twai_make_dual_filter"){.reference .internal}:

```{#codecell7}
// filter 1 id/mask 0x020, 0x7f0, receive only std id 0x02x
// filter 2 id/mask 0x013, 0x7f8, receive only std id 0x010~0x017
twai_mask_filter_config_t dual_config = twai_make_dual_filter(0x020, 0x7f0, 0x013, 0x7f8, false); // id1, mask1, id2, mask2, no extend ID
ESP_ERROR_CHECK(twai_node_config_mask_filter(node_hdl, 0, &dual_config));
```

### Bus Errors and Recovery

The TWAI controller can detect errors caused by bus interference or corrupted frames that do not conform to the frame format. It implements a fault isolation mechanism using transmit and receive error counters (TEC and REC). The values of these counters determine the node\'s error state: Error Active, Error Warning, Error Passive, and Bus Off. This mechanism ensures that nodes with persistent errors eventually disconnect themselves from the bus.

- **Error Active**: When both TEC and REC are less than 96, the node is in the active error state, meaning normal operation. The node participates in bus communication and sends **active error flags** when errors are detected to actively report them.

- **Error Warning**: When either TEC or REC is greater than or equal to 96 but both are less than 128, the node is in the warning error state. Errors may exist but the node behavior remains unchanged.

- **Error Passive**: When either TEC or REC is greater than or equal to 128, the node enters the passive error state. It can still communicate on the bus but sends only one **passive error flag** when detecting errors.

- **Bus Off**: When **TEC** is greater than or equal to 256, the node enters the bus off (offline) state. The node is effectively disconnected and does not affect the bus. It remains offline until recovery is triggered by software.

Software can retrieve the node status from tasks via the function [`twai_node_get_info()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv418twai_node_get_info18twai_node_handle_tP18twai_node_status_tP18twai_node_record_t "twai_node_get_info"){.reference .internal}. When the controller detects errors, it triggers the [`twai_event_callbacks_t::on_error`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N22twai_event_callbacks_t8on_errorE "twai_event_callbacks_t::on_error"){.reference .internal} callback, where the error data provides detailed information.

When the node's error state changes, the [`twai_event_callbacks_t::on_state_change`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N22twai_event_callbacks_t15on_state_changeE "twai_event_callbacks_t::on_state_change"){.reference .internal} callback is triggered, allowing the application to respond to the state transition. If the node is offline and needs recovery, call [`twai_node_recover()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv417twai_node_recover18twai_node_handle_t "twai_node_recover"){.reference .internal} from a task context. **Note that recovery is not immediate; the controller will automatically reconnect to the bus only after detecting 129 consecutive recessive bits (11 bits each).**

When recovery completes, the [`twai_event_callbacks_t::on_state_change`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N22twai_event_callbacks_t15on_state_changeE "twai_event_callbacks_t::on_state_change"){.reference .internal} callback will be triggered again, the node changes its state from [`TWAI_ERROR_BUS_OFF`{.xref .cpp .cpp-enumerator .docutils .literal .notranslate}](#_CPPv4N18twai_error_state_t18TWAI_ERROR_BUS_OFFE "TWAI_ERROR_BUS_OFF"){.reference .internal} to [`TWAI_ERROR_ACTIVE`{.xref .cpp .cpp-enumerator .docutils .literal .notranslate}](#_CPPv4N18twai_error_state_t17TWAI_ERROR_ACTIVEE "TWAI_ERROR_ACTIVE"){.reference .internal}. A recovered node can immediately resume transmissions; if there are pending tasks in the transmit queue, the driver will start transmitting them right away.

### Power Management

When power management is enabled via [CONFIG_PM_ENABLE](../kconfig-reference.html#config-pm-enable){.reference .internal}, the system may adjust or disable clock sources before entering sleep mode, which could cause TWAI to malfunction. To prevent this, the driver manages a power management lock internally. This lock is acquired when calling [`twai_node_enable()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv416twai_node_enable18twai_node_handle_t "twai_node_enable"){.reference .internal}, ensuring the system does not enter sleep mode and TWAI remains functional. To allow the system to enter a low-power state, call [`twai_node_disable()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv417twai_node_disable18twai_node_handle_t "twai_node_disable"){.reference .internal} to release the lock. During sleep, the TWAI controller will also stop functioning.

### Cache Safety

During Flash write operations, the system temporarily disables cache to prevent instruction and data fetch errors from Flash. This can cause interrupt handlers stored in Flash to become unresponsive. If you want interrupt routines to remain operational during cache-disabled periods, enable the [CONFIG_TWAI_ISR_CACHE_SAFE](../kconfig-reference.html#config-twai-isr-cache-safe){.reference .internal} option.

Note

When this option is enabled, **all interrupt callback functions and their context data must reside in internal memory**, because the system cannot fetch instructions or data from Flash while the cache is disabled.

### Thread Safety

The driver guarantees thread safety for all public TWAI APIs. You can safely call these APIs from different RTOS tasks without requiring additional synchronization or locking mechanisms.

### Performance

To improve the real-time performance of interrupt handling, the driver provides the [CONFIG_TWAI_ISR_IN_IRAM](../kconfig-reference.html#config-twai-isr-in-iram){.reference .internal} option. When enabled, the TWAI ISR (Interrupt Service Routine) and receive operations are placed in internal RAM, reducing latency caused by instruction fetching from Flash.

For applications that require high-performance transmit operations, the driver provides the [CONFIG_TWAI_IO_FUNC_IN_IRAM](../kconfig-reference.html#config-twai-io-func-in-iram){.reference .internal} option to place transmit functions in IRAM. This is particularly beneficial for time-critical applications that frequently call [`twai_node_transmit()`{.xref .cpp .cpp-func .docutils .literal .notranslate}](#_CPPv418twai_node_transmit18twai_node_handle_tPK12twai_frame_ti "twai_node_transmit"){.reference .internal} from user tasks.

Note

However, user-defined callback functions and context data invoked by the ISR may still reside in Flash. To fully eliminate Flash latency, users must place these functions and data into internal RAM using macros such as `IRAM_ATTR`{.xref .c .c-macro .docutils .literal .notranslate} for functions and `DRAM_ATTR`{.xref .c .c-macro .docutils .literal .notranslate} for data.

### Resource Usage

You can inspect the Flash and memory usage of the TWAI driver using the [IDF Size](../../api-guides/tools/idf-size.html){.reference .internal} tool. Below are the test conditions (based on the ESP32-C6 as an example):

- Compiler optimization level is set to `-Os`{.docutils .literal .notranslate} to minimize code size.

- Default log level is set to `ESP_LOG_INFO`{.docutils .literal .notranslate} to balance debugging information and performance.

- The following driver optimization options are disabled:

  > - [CONFIG_TWAI_ISR_IN_IRAM](../kconfig-reference.html#config-twai-isr-in-iram){.reference .internal} -- ISR is not placed in IRAM.
  > - [CONFIG_TWAI_ISR_CACHE_SAFE](../kconfig-reference.html#config-twai-isr-cache-safe){.reference .internal} -- Cache safety option is disabled.

**The following resource usage data is for reference only. Actual values may vary across different target chips.**

Component Layer Total Size DIRAM .bss .data .text Flash .rodata .text

---

driver 7262 12 12 0 0 7250 506 6744
hal 1952 0 0 0 0 0 0 1952
soc 64 0 0 0 0 64 64 0

Resource Usage with [CONFIG_TWAI_ISR_IN_IRAM](../kconfig-reference.html#config-twai-isr-in-iram){.reference .internal} Enabled:

Component Layer Total Size DIRAM .bss .data .text Flash .rodata .text

---

driver 7248 692 12 0 680 6556 506 6050
hal 1952 1030 0 0 1030 922 0 922
soc 64 0 0 0 0 0 64 0

Additionally, each TWAI handle dynamically allocates approximately `168`{.docutils .literal .notranslate} + 4 \* [`twai_onchip_node_config_t::tx_queue_depth`{.xref .cpp .cpp-member .docutils .literal .notranslate}](#_CPPv4N25twai_onchip_node_config_t14tx_queue_depthE "twai_onchip_node_config_t::tx_queue_depth"){.reference .internal} bytes of memory from the heap.

### Other Kconfig Options

- [CONFIG_TWAI_ENABLE_DEBUG_LOG](../kconfig-reference.html#config-twai-enable-debug-log){.reference .internal}: This option forces all debug logs of the TWAI driver to be enabled regardless of the global log level settings. Enabling this can help developers obtain more detailed log information during debugging, making it easier to locate and resolve issues.

## Application Examples

- [peripherals/twai/twai_utils](https://github.com/espressif/esp-idf/tree/v6.0.1/examples/peripherals/twai/twai_utils){.reference .external} demonstrates how to use the TWAI (Two-Wire Automotive Interface) APIs to create a command-line interface for TWAI bus communication, supporting frame transmission/reception, filtering, monitoring, and both classic and FD formats for testing and debugging TWAI networks.

- [peripherals/twai/twai_error_recovery](https://github.com/espressif/esp-idf/tree/v6.0.1/examples/peripherals/twai/twai_error_recovery){.reference .external} demonstrates how to recover nodes from the bus-off state and resume communication, as well as bus error reporting, node state changes, and other event information.

- [peripherals/twai/twai_network](https://github.com/espressif/esp-idf/tree/v6.0.1/examples/peripherals/twai/twai_network){.reference .external} using 2 nodes with different roles: transmitting and listening, demonstrates how to use the driver for single and bulk data transmission, as well as configure filters to receive these data.

- [peripherals/twai/cybergear](https://github.com/espressif/esp-idf/tree/v6.0.1/examples/peripherals/twai/cybergear){.reference .external} demonstrates how to control XiaoMi CyberGear motors via TWAI interface.

## API Reference

### On-Chip TWAI APIs

#### Header File

- [components/esp_driver_twai/include/esp_twai_onchip.h](https://github.com/espressif/esp-idf/blob/v6.0.1/components/esp_driver_twai/include/esp_twai_onchip.h){.reference .external}

- This header file can be included with:

  > ```{#codecell8}
  > #include "esp_twai_onchip.h"
  > ```

- This header file is a part of the API provided by the `esp_driver_twai`{.docutils .literal .notranslate} component. To declare that your component depends on `esp_driver_twai`{.docutils .literal .notranslate}, add the following to your CMakeLists.txt:

  > ```{#codecell9}
  > REQUIRES esp_driver_twai
  > ```
  >
  > or
  >
  > ```{#codecell10}
  > PRIV_REQUIRES esp_driver_twai
  > ```

#### Functions

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_new_node_onchip(const [twai_onchip_node_config_t](#_CPPv425twai_onchip_node_config_t "twai_onchip_node_config_t"){.reference .internal} \*node_config, [twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} \*node_ret)\

: Allocate a TWAI hardware node by specific init config structure To delete/free the TWAI, call `twai_node_delete()`{.docutils .literal .notranslate}

    Parameters:

    :   - **node_config** \-- **\[in\]** Init config structure

        - **node_ret** \-- **\[out\]** Return driver handle

    Returns:

    :   ESP_OK Allocate success ESP_ERR_NO_MEM No enough free memory ESP_ERR_NOT_FOUND No free hardware controller ESP_ERR_INVALID_ARG Config argument not available ESP_ERR_INVALID_STATE State error, including hardware state error and driver state error ESP_FAIL Other reasons

&nbsp;

static inline [twai_mask_filter_config_t](#_CPPv425twai_mask_filter_config_t "twai_mask_filter_config_t"){.reference .internal} twai_make_dual_filter(uint32_t id1, uint32_t mask1, uint32_t id2, uint32_t mask2, bool is_ext)\

: Helper function to configure a dual 16-bit acceptance filter.

    Note

    For 29bits Extended IDs, ONLY high 16bits id/mask is used for each filter.

    Parameters:

    :   - **id1** \-- First full 11/29 bits ID to filter.

        - **mask1** \-- Mask for first ID.

        - **id2** \-- Second full 11/29 bits ID to filter.

        - **mask2** \-- Mask for second ID.

        - **is_ext** \-- True if using Extended (29-bit) IDs, false for Standard (11-bit) IDs.

    Returns:

    :   [twai_mask_filter_config_t](#structtwai__mask__filter__config__t){.reference .internal} A filled filter configuration structure for dual filtering.

#### Structures

struct twai_onchip_node_config_t\

: TWAI on-chip node initialization configuration structure.

    Public Members

    gpio_num_t tx\

    :   GPIO pin for twai TX

    &nbsp;

    gpio_num_t rx\

    :   GPIO pin for twai RX

    &nbsp;

    gpio_num_t quanta_clk_out\

    :   GPIO pin for quanta clock output, Set -1 to not use

    &nbsp;

    gpio_num_t bus_off_indicator\

    :   GPIO pin for bus-off indicator, Set -1 to not use

    &nbsp;

    struct [twai_onchip_node_config_t](#_CPPv425twai_onchip_node_config_t "twai_onchip_node_config_t"){.reference .internal} io_cfg\

    :   I/O configuration

    &nbsp;

    [twai_clock_source_t](#_CPPv419twai_clock_source_t "twai_clock_source_t"){.reference .internal} clk_src\

    :   Optional, clock source, remain 0 to using TWAI_CLK_SRC_DEFAULT by default

    &nbsp;

    [twai_timing_basic_config_t](#_CPPv426twai_timing_basic_config_t "twai_timing_basic_config_t"){.reference .internal} bit_timing\

    :   Timing configuration for classic twai and FD arbitration stage

    &nbsp;

    [twai_timing_basic_config_t](#_CPPv426twai_timing_basic_config_t "twai_timing_basic_config_t"){.reference .internal} data_timing\

    :   Optional, timing configuration for FD data stage

    &nbsp;

    uint32_t timestamp_resolution_hz\

    :   Timebase frequency (in Hz), used for recording the timestamp of RX frame, set 0 to disable the timestamp feature

    &nbsp;

    int8_t fail_retry_cnt\

    :   Hardware retry limit if failed, range \[-1:15\], -1 for re-trans forever

    &nbsp;

    uint32_t tx_queue_depth\

    :   Depth of the transmit queue

    &nbsp;

    int intr_priority\

    :   Interrupt priority, \[0:3\]

    &nbsp;

    uint32_t enable_self_test\

    :   Transmission does not require acknowledgment. Use this mode for self testing

    &nbsp;

    uint32_t enable_loopback\

    :   The TWAI controller receives back frames that it sends out, but does not acknowledge them

    &nbsp;

    uint32_t enable_listen_only\

    :   No transmissions or acknowledgements. The controller only monitors the bus without participating

    &nbsp;

    uint32_t no_receive_rtr\

    :   Don\'t receive remote frames

    &nbsp;

    uint32_t sleep_allow_pd\

    :   Allow power down during sleep to save power, driver will backup/restore the TWAI registers to guarantee the peripheral features.

    &nbsp;

    struct [twai_onchip_node_config_t](#_CPPv425twai_onchip_node_config_t "twai_onchip_node_config_t"){.reference .internal} flags\

    :   Misc configuration flags

### TWAI Driver APIs

#### Header File

- [components/esp_driver_twai/include/esp_twai.h](https://github.com/espressif/esp-idf/blob/v6.0.1/components/esp_driver_twai/include/esp_twai.h){.reference .external}

- This header file can be included with:

  > ```{#codecell11}
  > #include "esp_twai.h"
  > ```

- This header file is a part of the API provided by the `esp_driver_twai`{.docutils .literal .notranslate} component. To declare that your component depends on `esp_driver_twai`{.docutils .literal .notranslate}, add the following to your CMakeLists.txt:

  > ```{#codecell12}
  > REQUIRES esp_driver_twai
  > ```
  >
  > or
  >
  > ```{#codecell13}
  > PRIV_REQUIRES esp_driver_twai
  > ```

#### Functions

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_enable([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node)\

: Enable the TWAI node.

    Parameters:

    :   **node** \-- Handle to the TWAI node

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Node already in enabled state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_disable([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node)\

: Disable the TWAI node.

    Parameters:

    :   **node** \-- Handle to the TWAI node

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Node not in enabled state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_recover([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node)\

: Init the recover process for TWAI node which in bus-off.

    Note

    Follow `on_state_change`{.docutils .literal .notranslate} callback or `twai_node_get_info`{.docutils .literal .notranslate} to know recover finish or not

    Parameters:

    :   **node** \-- Handle to the TWAI node

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Node not in bus-off state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_delete([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node)\

: Delete the TWAI node and release resources.

    Parameters:

    :   **node** \-- Handle to the TWAI node

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Node not in disabled state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_register_event_callbacks([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, const [twai_event_callbacks_t](#_CPPv422twai_event_callbacks_t "twai_event_callbacks_t"){.reference .internal} \*cbs, void \*user_data)\

: Register event callbacks for the TWAI node.

    Parameters:

    :   - **node** \-- Handle to the TWAI node

        - **cbs** \-- Pointer to a structure of event callback functions

        - **user_data** \-- User-defined data passed to callback functions

    Returns:

    :   ESP_OK on success, error code otherwise

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_reconfig_timing([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, const [twai_timing_advanced_config_t](#_CPPv429twai_timing_advanced_config_t "twai_timing_advanced_config_t"){.reference .internal} \*bit_timing, const [twai_timing_advanced_config_t](#_CPPv429twai_timing_advanced_config_t "twai_timing_advanced_config_t"){.reference .internal} \*data_timing)\

: Reconfigure the timing settings of the TWAI node.

    Note

    You can reconfigure the timing for the arbitration and data phase, separately or together.

    Parameters:

    :   - **node** \-- Handle to the TWAI node

        - **bit_timing** \-- Optional,pointer to new twai cc(classic) or arbitration phase of twai fd timing configuration

        - **data_timing** \-- Optional, pointer to new twai fd timing configuration

    Returns:

    :   ESP_OK on success, error code otherwise

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_config_mask_filter([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, uint8_t filter_id, const [twai_mask_filter_config_t](#_CPPv425twai_mask_filter_config_t "twai_mask_filter_config_t"){.reference .internal} \*mask_cfg)\

: Configure the mask filter of the TWAI node.

    Parameters:

    :   - **node** \-- Handle to the TWAI node

        - **filter_id** \-- Index of the filter to configure

        - **mask_cfg** \-- Pointer to the mask filter configuration

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_ARG: Invalid argument

        - ESP_ERR_INVALID_STATE: Node not in disabled state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_config_range_filter([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, uint8_t filter_id, const [twai_range_filter_config_t](#_CPPv426twai_range_filter_config_t "twai_range_filter_config_t"){.reference .internal} \*range_cfg)\

: Configure the range filter of the TWAI node.

    Parameters:

    :   - **node** \-- Handle to the TWAI node

        - **filter_id** \-- Index of the filter to configure

        - **range_cfg** \-- Pointer to the range filter configuration

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_ARG: Invalid argument

        - ESP_ERR_INVALID_STATE: Node not in disabled state

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_get_info([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, [twai_node_status_t](#_CPPv418twai_node_status_t "twai_node_status_t"){.reference .internal} \*status_ret, [twai_node_record_t](#_CPPv418twai_node_record_t "twai_node_record_t"){.reference .internal} \*statistics_ret)\

: Get information about the TWAI node.

    Parameters:

    :   - **node** \-- Handle to the TWAI node

        - **status_ret** \-- Pointer to store the current node status

        - **statistics_ret** \-- Pointer to store node statistics

    Returns:

    :   ESP_OK on success, error code otherwise

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_transmit([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, const [twai_frame_t](#_CPPv412twai_frame_t "twai_frame_t"){.reference .internal} \*frame, int timeout_ms)\

: Transmit a TWAI frame.

    Parameters:

    :   - **node** \-- **\[in\]** Handle to the TWAI node

        - **frame** \-- **\[in\]** Pointer to the frame to transmit

        - **timeout_ms** \-- **\[in\]** Maximum wait time if the transmission queue is full (milliseconds), -1 to wait forever

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_ARG: Invalid argument

        - ESP_ERR_INVALID_STATE: Node already in bus-off state

        - ESP_ERR_NOT_SUPPORTED: Node is config as listen only

        - ESP_ERR_TIMEOUT: Timeout to wait for queue space

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_transmit_wait_all_done([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, int timeout_ms)\

: Wait for all pending transfers to finish, if bus-off happens during waiting, wait until node recovered and tx is finished, or timeout.

    Parameters:

    :   - **node** \-- **\[in\]** Handle to the TWAI node

        - **timeout_ms** \-- **\[in\]** Maximum wait time for all pending transfers to finish (milliseconds), -1 to wait forever

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Node already in bus-off state

        - ESP_ERR_TIMEOUT: Timeout

&nbsp;

[esp_err_t](../system/esp_err.html#_CPPv49esp_err_t "esp_err_t"){.reference .internal} twai_node_receive_from_isr([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} node, [twai_frame_t](#_CPPv412twai_frame_t "twai_frame_t"){.reference .internal} \*rx_frame)\

: Receive a TWAI frame from \'rx_done_cb\'.

    Note

    This function can only be called from the `rx_done_cb`{.docutils .literal .notranslate} callback, you can\'t call it from a task.

    Note

    Please also provide `buffer`{.docutils .literal .notranslate} and `buffer_len`{.docutils .literal .notranslate} inside the rx_frame

    Note

    Can get original data length from `twaifd_dlc2len(rx_frame.header.dlc)`{.docutils .literal .notranslate}

    Parameters:

    :   - **node** \-- **\[in\]** Handle to the TWAI node

        - **rx_frame** \-- **\[out\]** Pointer to the frame store rx content

    Returns:

    :   \- ESP_OK: Success

        - ESP_ERR_INVALID_STATE: Called from a task or from other callbacks except `rx_done_cb`{.docutils .literal .notranslate}

### TWAI Driver Types

#### Header File

- [components/esp_driver_twai/include/esp_twai_types.h](https://github.com/espressif/esp-idf/blob/v6.0.1/components/esp_driver_twai/include/esp_twai_types.h){.reference .external}

- This header file can be included with:

  > ```{#codecell14}
  > #include "esp_twai_types.h"
  > ```

- This header file is a part of the API provided by the `esp_driver_twai`{.docutils .literal .notranslate} component. To declare that your component depends on `esp_driver_twai`{.docutils .literal .notranslate}, add the following to your CMakeLists.txt:

  > ```{#codecell15}
  > REQUIRES esp_driver_twai
  > ```
  >
  > or
  >
  > ```{#codecell16}
  > PRIV_REQUIRES esp_driver_twai
  > ```

#### Structures

struct twai_timing_basic_config_t\

: TWAI bitrate timing config basic (simple) mode.

    Public Members

    uint32_t bitrate\

    :   Expected TWAI bus baud_rate/bitrate in bits/second

    &nbsp;

    uint16_t sp_permill\

    :   Optional, sampling point in permill (1/1000) of the entire bit time

    &nbsp;

    uint16_t ssp_permill\

    :   Optional, secondary sample point(ssp) in permill (1/1000) of the entire bit time

&nbsp;

struct twai_frame_t\

: TWAI transaction frame param type.

    Public Members

    [twai_frame_header_t](#_CPPv419twai_frame_header_t "twai_frame_header_t"){.reference .internal} header\

    :   message attribute/metadata, exclude data buffer

    &nbsp;

    uint8_t \*buffer\

    :   buffer address for tx and rx message data

    &nbsp;

    size_t buffer_len\

    :   buffer length of provided data buffer pointer, in bytes.

&nbsp;

struct twai_node_status_t\

: TWAI node\'s status.

    Public Members

    [twai_error_state_t](#_CPPv418twai_error_state_t "twai_error_state_t"){.reference .internal} state\

    :   Node\'s error state

    &nbsp;

    uint16_t tx_error_count\

    :   Node\'s TX error count

    &nbsp;

    uint16_t rx_error_count\

    :   Node\'s RX error count

    &nbsp;

    uint32_t tx_queue_remaining\

    :   Node\'s TX queue remaining frame space (number of frames)

&nbsp;

struct twai_node_record_t\

: TWAI node\'s statistics/record type.

    This structure contains some statistics regarding a node\'s communication on the TWAI bus

    Public Members

    uint32_t bus_err_num\

    :   Cumulative number (since `twai_node_enable()`{.docutils .literal .notranslate}) of bus errors

&nbsp;

struct twai_tx_done_event_data_t\

: TWAI \"TX done\" event data.

    Public Members

    bool is_tx_success\

    :   Indicate if frame send successful, refer `on_error`{.docutils .literal .notranslate} callback for fail reason if send failed

    &nbsp;

    const [twai_frame_t](#_CPPv412twai_frame_t "twai_frame_t"){.reference .internal} \*done_tx_frame\

    :   Pointer to the frame that has been transmitted

&nbsp;

struct twai_rx_done_event_data_t\

: TWAI \"RX done\" event data.

&nbsp;

struct twai_state_change_event_data_t\

: TWAI \"state change\" event data.

    Public Members

    [twai_error_state_t](#_CPPv418twai_error_state_t "twai_error_state_t"){.reference .internal} old_sta\

    :   Previous error state

    &nbsp;

    [twai_error_state_t](#_CPPv418twai_error_state_t "twai_error_state_t"){.reference .internal} new_sta\

    :   New error state after the change

&nbsp;

struct twai_error_event_data_t\

: TWAI \"error\" event data.

    Public Members

    [twai_error_flags_t](#_CPPv418twai_error_flags_t "twai_error_flags_t"){.reference .internal} err_flags\

    :   Error flags indicating the type of the error

&nbsp;

struct twai_event_callbacks_t\

: Group of supported TWAI callbacks.

    Note

    All of these callbacks is invoked from ISR context. Thus, the implementation of the callback function must adhere to the ISR restrictions such as not calling any blocking APIs.

    Note

    Set the particular event callback\'s entry to NULL to unregister it if not required.

    Note

    When TWAI_ISR_CACHE_SAFE is enabled, the callbacks must be placed in IRAM.

    Public Members

    bool (\*on_tx_done)([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} handle, const [twai_tx_done_event_data_t](#_CPPv425twai_tx_done_event_data_t "twai_tx_done_event_data_t"){.reference .internal} \*edata, void \*user_ctx)\

    :   TWAI \"TX done\" event callback prototype.

        Param handle:

        :   TWAI node handle

        Param edata:

        :   \"TX done\" event data (passed by the driver)

        Param user_ctx:

        :   User data, passed from `twai_node_register_event_callbacks()`{.docutils .literal .notranslate}

        Return:

        :   Whether a higher priority task has been unblocked by this function

    &nbsp;

    bool (\*on_rx_done)([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} handle, const [twai_rx_done_event_data_t](#_CPPv425twai_rx_done_event_data_t "twai_rx_done_event_data_t"){.reference .internal} \*edata, void \*user_ctx)\

    :   TWAI \"RX done\" event callback prototype.

        Param handle:

        :   TWAI node handle

        Param edata:

        :   \"RX done\" event data (passed by the driver)

        Param user_ctx:

        :   User data, passed from `twai_node_register_event_callbacks()`{.docutils .literal .notranslate}

        Return:

        :   Whether a higher priority task has been unblocked by this function

    &nbsp;

    bool (\*on_state_change)([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} handle, const [twai_state_change_event_data_t](#_CPPv430twai_state_change_event_data_t "twai_state_change_event_data_t"){.reference .internal} \*edata, void \*user_ctx)\

    :   TWAI \"state change\" event callback prototype.

        Param handle:

        :   TWAI node handle

        Param edata:

        :   \"state change\" event data (passed by the driver)

        Param user_ctx:

        :   User data, passed from `twai_node_register_event_callbacks()`{.docutils .literal .notranslate}

        Return:

        :   Whether a higher priority task has been unblocked by this function

    &nbsp;

    bool (\*on_error)([twai_node_handle_t](#_CPPv418twai_node_handle_t "twai_node_handle_t"){.reference .internal} handle, const [twai_error_event_data_t](#_CPPv423twai_error_event_data_t "twai_error_event_data_t"){.reference .internal} \*edata, void \*user_ctx)\

    :   TWAI \"error\" event callback prototype.

        Param handle:

        :   **\[in\]** TWAI node handle

        Param edata:

        :   **\[in\]** \"error\" event data (passed by the driver)

        Param user_ctx:

        :   **\[in\]** User data, passed from `twai_node_register_event_callbacks()`{.docutils .literal .notranslate}

        Return:

        :   Whether a higher priority task has been unblocked by this function

#### Type Definitions

typedef struct twai_node_base \*twai_node_handle_t\

: ESP TWAI controller handle.

### TWAI HAL Types

#### Header File

- [components/esp_hal_twai/include/hal/twai_types.h](https://github.com/espressif/esp-idf/blob/v6.0.1/components/esp_hal_twai/include/hal/twai_types.h){.reference .external}

- This header file can be included with:

  > ```{#codecell17}
  > #include "hal/twai_types.h"
  > ```

- This header file is a part of the API provided by the `esp_hal_twai`{.docutils .literal .notranslate} component. To declare that your component depends on `esp_hal_twai`{.docutils .literal .notranslate}, add the following to your CMakeLists.txt:

  > ```{#codecell18}
  > REQUIRES esp_hal_twai
  > ```
  >
  > or
  >
  > ```{#codecell19}
  > PRIV_REQUIRES esp_hal_twai
  > ```

#### Functions

static inline uint16_t twaifd_dlc2len(uint16_t dlc)\

: Translate TWAIFD format DLC code to bytes length.

    Parameters:

    :   **dlc** \-- **\[in\]** The frame DLC code follow the FD spec

    Returns:

    :   The byte length of DLC stand for

&nbsp;

static inline uint16_t twaifd_len2dlc(uint16_t byte_len)\

: Translate TWAIFD format bytes length to DLC code.

    Parameters:

    :   **byte_len** \-- **\[in\]** The byte length of the message

    Returns:

    :   The FD adopted frame DLC code

#### Unions

union twai_error_flags_t\

: _#include \<twai_types.h\>_

    TWAI transmit error type structure.

    Public Members

    uint32_t arb_lost\

    :   Arbitration lost error (lost arbitration during transmission)

    &nbsp;

    uint32_t bit_err\

    :   Bit error detected (dominant/recessive mismatch during transmission)

    &nbsp;

    uint32_t form_err\

    :   Form error detected (frame fixed-form bit violation)

    &nbsp;

    uint32_t stuff_err\

    :   Stuff error detected (e.g. dominant error frame received)

    &nbsp;

    uint32_t ack_err\

    :   ACK error (no ack), transmission without acknowledge received

    &nbsp;

    struct twai_error_flags_t

    :

    &nbsp;

    uint32_t val\

    :   Integrated error flags

#### Structures

struct twai_timing_advanced_config_t\

: TWAI bitrate timing advanced config structure.

    Public Members

    uint32_t brp\

    :   Bitrate pre-divider, which decides the quanta time

    &nbsp;

    uint8_t prop_seg\

    :   Prop_seg length, in quanta time

    &nbsp;

    uint8_t tseg_1\

    :   Seg_1 length, in quanta time

    &nbsp;

    uint8_t tseg_2\

    :   Seg_2 length, in quanta time

    &nbsp;

    uint8_t sjw\

    :   Sync jump width, in quanta time

    &nbsp;

    uint8_t ssp_offset\

    :   Secondary sample point offset refet to Sync seg, in quanta time, set 0 to disable ssp

&nbsp;

struct twai_mask_filter_config_t\

: Configuration for TWAI mask filter.

    Public Members

    uint32_t id\

    :   Single base ID for filtering

    &nbsp;

    uint32_t \*id_list\

    :   Base ID list array for filtering, which share the same `mask`{.docutils .literal .notranslate}

    &nbsp;

    uint32_t num_of_ids\

    :   List length of `id_list`{.docutils .literal .notranslate}, remain empty to using single `id`{.docutils .literal .notranslate} instead of `id_list`{.docutils .literal .notranslate}

    &nbsp;

    uint32_t mask\

    :   Mask to determine the matching bits (1 = match bit, 0 = any bit)

    &nbsp;

    uint32_t is_ext\

    :   True for extended ID filtering, false for standard ID

    &nbsp;

    uint32_t no_classic\

    :   If true, Classic TWAI frames are excluded (only TWAI FD allowed)

    &nbsp;

    uint32_t no_fd\

    :   If true, TWAI FD frames are excluded (only Classic TWAI allowed)

    &nbsp;

    uint32_t dual_filter\

    :   Set filter as dual-16bits filter mode, see `twai_make_dual_filter()`{.docutils .literal .notranslate} for easy config

&nbsp;

struct twai_range_filter_config_t\

: Range-based filter configuration structure.

    Public Members

    uint32_t range_low\

    :   Lower bound of the ID filtering range, included

    &nbsp;

    uint32_t range_high\

    :   Upper bound of the ID filtering range, included

    &nbsp;

    uint32_t is_ext\

    :   True for extended ID filtering, false for standard ID

    &nbsp;

    uint32_t no_classic\

    :   If true, Classic TWAI frames are excluded (only TWAI FD allowed)

    &nbsp;

    uint32_t no_fd\

    :   If true, TWAI FD frames are excluded (only Classic TWAI allowed)

&nbsp;

struct twai_frame_header_t\

: TWAI frame header/format struct type.

    Public Members

    uint32_t id\

    :   message arbitration identification

    &nbsp;

    uint16_t dlc\

    :   message data length code

    &nbsp;

    uint32_t ide\

    :   Extended Frame Format (29bit ID)

    &nbsp;

    uint32_t rtr\

    :   Message is a Remote Frame

    &nbsp;

    uint32_t fdf\

    :   Message is FD format, allow max 64 byte of data

    &nbsp;

    uint32_t brs\

    :   Transmit message with Bit Rate Shift.

    &nbsp;

    uint32_t esi\

    :   Transmit side error indicator for received frame

    &nbsp;

    uint64_t timestamp\

    :   Timestamp for received message

    &nbsp;

    uint64_t trigger_time\

    :   Trigger time for transmitting message

#### Macros

TWAI_STD_ID_MASK\

: Mask of the ID fields in a standard frame

&nbsp;

TWAI_EXT_ID_MASK\

: Mask of the ID fields in an extended frame

&nbsp;

TWAI_FRAME_MAX_DLC\

:

&nbsp;

TWAI_FRAME_MAX_LEN\

:

&nbsp;

TWAIFD_FRAME_MAX_DLC\

:

&nbsp;

TWAIFD_FRAME_MAX_LEN\

:

#### Type Definitions

typedef [soc_periph_twai_clk_src_t](clk_tree.html#_CPPv425soc_periph_twai_clk_src_t "soc_periph_twai_clk_src_t"){.reference .internal} twai_clock_source_t\

: TWAI group clock source.

    Note

    User should select the clock source based on the power and resolution requirement

#### Enumerations

enum twai_error_state_t\

: TWAI node error fsm states.

    *Values:*

    enumerator TWAI_ERROR_ACTIVE\

    :   Error active state: TEC/REC \< 96

    enumerator TWAI_ERROR_WARNING\

    :   Error warning state: TEC/REC \>= 96 and \< 128

    enumerator TWAI_ERROR_PASSIVE\

    :   Error passive state: TEC/REC \>= 128 and \< 256

    enumerator TWAI_ERROR_BUS_OFF\

    :   Bus-off state: TEC \>= 256 (node offline)
