// Rickie Kenrdt <rkerndt@cs.uoregon.edu>
// ssh_relay.h
// Particle Electron app to relay ssh connections throug seial ports


#define PUBLISH_PERIOD 60000 // 1 hour

#define STATUS_INIT         0
#define STATUS_DISCONNECTED 1
#define STATUS_CONNECTED    2
#define STATUS_SSH_SESSION  3

#define NAME_STATUS          "status"
#define NAME_CONN_ATTEMPTS   "attempts"
#define NAME_CONN_ACCEPT     "accepted"
#define NAME_CONN_REJECT     "rejected"
#define NAME_LOCAL_IP_ADDR   "local_ip"
#define NAME_PUBLIC_IP_ADDR  "public_ip"
#define NAME_PUBLIC_IP_TOPIC "spark/device/ip"
#define NAME_GET_PUBLIC_IP   "get_ip"

// Function declarations
void publish_updates(void);
String ip_to_string(IPAddress);
void handler(const char*, const char*);
int get_public_ip(String);
