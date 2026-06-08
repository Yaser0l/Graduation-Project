#include "esp_isotp_stubs.h"

#include <stdbool.h>
#include <string.h>

#include "isotp.h"

static bool s_new_transport_fail = false;
static int s_isotp_send_ret = ISOTP_RET_OK;
static int s_isotp_receive_ret = ISOTP_RET_NO_DATA;
static int s_send_calls = 0;
static int s_receive_calls = 0;
static uint8_t s_last_send_payload[256] = {0};
static uint32_t s_last_send_len = 0;

static uint8_t s_rx_queue[16][256] = {0};
static uint32_t s_rx_lens[16] = {0};
static int s_rx_queue_head = 0;
static int s_rx_queue_tail = 0;

static int s_on_can_message_calls = 0;
static bool s_next_receive_empty = false;

void isotp_stub_reset(void) {
    s_new_transport_fail = false;
    s_isotp_send_ret = ISOTP_RET_OK;
    s_isotp_receive_ret = ISOTP_RET_NO_DATA;
    s_send_calls = 0;
    s_receive_calls = 0;
    memset(s_last_send_payload, 0, sizeof(s_last_send_payload));
    s_last_send_len = 0;
    memset(s_rx_queue, 0, sizeof(s_rx_queue));
    memset(s_rx_lens, 0, sizeof(s_rx_lens));
    s_rx_queue_head = 0;
    s_rx_queue_tail = 0;
    s_on_can_message_calls = 0;
    s_next_receive_empty = false;
}

void isotp_stub_set_new_transport_result(int result) {
    s_new_transport_fail = (result != 0);
}

void isotp_stub_set_send_result(int result) { s_isotp_send_ret = result; }
void isotp_stub_set_receive_result(int result) { s_isotp_receive_ret = result; }
int isotp_stub_get_send_calls(void) { return s_send_calls; }
int isotp_stub_get_receive_calls(void) { return s_receive_calls; }
uint32_t isotp_stub_get_last_send_len(void) { return s_last_send_len; }
const uint8_t* isotp_stub_get_last_send_payload(void) { return s_last_send_payload; }

void isotp_stub_queue_rx(const uint8_t* data, uint32_t len) {
    if (s_rx_queue_tail >= 16) return;
    if (data && len > 0) {
        memcpy(s_rx_queue[s_rx_queue_tail], data, len > 256 ? 256 : len);
        s_rx_lens[s_rx_queue_tail] = len;
    } else {
        s_rx_lens[s_rx_queue_tail] = 0;
    }
    s_rx_queue_tail++;
}

void isotp_init_link(IsoTpLink* link, uint32_t sendid, uint8_t* sendbuf,
                     uint32_t sendbufsize, uint8_t* recvbuf, uint32_t recvbufsize) {
    (void)sendid;
    memset(link, 0, sizeof(*link));
    if (s_new_transport_fail) return;
    link->send_buffer = sendbuf;
    link->send_buf_size = sendbufsize;
    link->receive_buffer = recvbuf;
    link->receive_buf_size = recvbufsize;
    link->send_status = ISOTP_SEND_STATUS_IDLE;
    link->receive_status = ISOTP_RECEIVE_STATUS_IDLE;
}

void isotp_destroy_link(IsoTpLink* link) { (void)link; }

void isotp_poll(IsoTpLink* link) { (void)link; }

int isotp_send(IsoTpLink* link, const uint8_t payload[], uint32_t size) {
    (void)link;
    s_send_calls++;
    if (payload && size > 0) {
        memcpy(s_last_send_payload, payload, size > 255 ? 255 : size);
        s_last_send_len = size;
    }
    return s_isotp_send_ret;
}

int isotp_send_with_id(IsoTpLink* link, uint32_t id, const uint8_t payload[],
                       uint32_t size) {
    (void)link; (void)id;
    s_send_calls++;
    if (payload && size > 0) {
        memcpy(s_last_send_payload, payload, size > 255 ? 255 : size);
        s_last_send_len = size;
    }
    return s_isotp_send_ret;
}

int isotp_receive(IsoTpLink* link, uint8_t* payload, const uint32_t payload_size,
                   uint32_t* out_size) {
    s_receive_calls++;
    if (s_next_receive_empty) {
        s_next_receive_empty = false;
        if (out_size) *out_size = 0;
        return ISOTP_RET_OK;
    }
    if (s_rx_queue_head >= s_rx_queue_tail) {
        if (out_size) *out_size = 0;
        return ISOTP_RET_NO_DATA;
    }
    uint32_t len = s_rx_lens[s_rx_queue_head];
    if (len == 0) {
        s_rx_queue_head++;
        if (out_size) *out_size = 0;
        return ISOTP_RET_NO_DATA;
    }
    if (len > payload_size) len = payload_size;
    memcpy(payload, s_rx_queue[s_rx_queue_head], len);
    if (out_size) *out_size = len;
    s_rx_queue_head++;
    return ISOTP_RET_OK;
}

void isotp_on_can_message(IsoTpLink* link, const uint8_t* data, uint8_t len) {
    (void)link; (void)data; (void)len;
    s_on_can_message_calls++;
}

int isotp_stub_get_on_can_message_calls(void) { return s_on_can_message_calls; }

void isotp_stub_set_next_receive_empty(void) { s_next_receive_empty = true; }
