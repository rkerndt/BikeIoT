// Rickie Kerndt <rkerndt@cs.uoregon.edu>
//
// Particle Electron app to relay ssh conections through serial port
//

#include "ssh_relay.h"

// Global Published Variables
int status = 0;
int connect_attempts = 0;
int connect_accepted = 0;
int connect_rejected = 0;
String local_ip_str("0.0.0.0");
String public_ip_str("0.0.0.0");

// Valid connecting ip address
String ip_list[] = { String("70.240.52.134"),
                     nullptr };

// SSH relay 
TCPServer server = TCPServer(22);
TCPClient client;
uint8_t in_buf[1500];
uint8_t ou_buf[1500];


void setup() {
  Serial.begin(115200);
  Particle.variable(NAME_STATUS, status);
  Particle.variable(NAME_CONN_ATTEMPTS, connect_attempts);
  Particle.variable(NAME_CONN_ACCEPT, connect_accepted);
  Particle.variable(NAME_CONN_REJECT, connect_rejected);
  Particle.variable(NAME_LOCAL_IP_ADDR, local_ip_str);
  Particle.variable(NAME_PUBLIC_IP_ADDR, public_ip_str);
  Particle.function(NAME_GET_PUBLIC_IP, get_public_ip);

  while ( !Cellular.ready() )
  {
    Particle.process();
  }
  Particle.subscribe("spark/", handler);
  server.begin();
  Serial.println("Listing on port 22");
}

void loop() {

  // publish our ip addresses
  if ( Cellular.ready() )
  {
    if (status < STATUS_CONNECTED)
    {
      status = STATUS_CONNECTED;
      local_ip_str = ip_to_string(Cellular.localIP());
      Particle.publish(NAME_PUBLIC_IP_TOPIC);
    }
  }
  else if (status >= STATUS_CONNECTED)
  {
    status = STATUS_DISCONNECTED;
    local_ip_str = String("0.0.0.0");
    public_ip_str = String("0.0.0.0");
  }

  // echo back packets for anyone connected
  if ( client.connected() )
  {
    int num_read = client.read(in_buf, sizeof(in_buf));
    if ( num_read > 0 )
    {
      server.write(in_buf, num_read);
      Serial.write(in_buf, num_read);
    }
  }
  else
  {
    client = server.available();
    if ( client.connected() )
    {
      String remote_ip_str = ip_to_string(client.remoteIP());
      if ( !check_ip(remote_ip_str) )
      {
        client.stop();
        Serial.print("Denied connection from ");
      }
      else
      {
        Serial.print("Accepted connection from ");
      }
      Serial.println(client.remoteIP());
      client.println("Welcome");
    }
  }
}

void publish_updates() {
  Particle.publish(NAME_STATUS, String(status));
  Particle.publish(NAME_CONN_ATTEMPTS, String(connect_attempts));
  Particle.publish(NAME_CONN_ACCEPT, String(connect_accepted));
  Particle.publish(NAME_CONN_REJECT, String(connect_rejected));
}

String ip_to_string(IPAddress ipaddr) {
  String s = String(ipaddr[0])+"."+String(ipaddr[1])+"."+String(ipaddr[2])+"."+String(ipaddr[3]);
  return s;
}

bool string_to_ip(String ipaddr, IPAddress *ip) {
  // TODO check for valid digits
  String ip_str[4];
  bool still_good = True;
  split_string(ipaddr, '.', ip_str, 4);
  for (int i = 0; (i < 4) && (ip != nullptr); ++i)
  {
    if (ip == nullptr)
    {
      still_good = false;
      break;
    }
    ip[i] = ip_str->toInt();
  }

}

int get_public_ip(String s)
{
  Serial.println("Requesting public ip");
  bool result = Particle.publish(NAME_PUBLIC_IP_TOPIC);
  return (result == true) ? 1 : 0;
}

bool check_ip(String ip) {
  String *ip_list_ptr = ip_list;
  bool result = false;
  while ( (ip_list_ptr != nullptr) && !result)
  {
    result = ip.startsWith(*ip_list_ptr);
    ++ip_list_ptr;
  }
  return result;
}

int send_alive(String arg_list) {
  String argv[3];
  int still_good = true;

}

void send_udp_packet(IPAddress ipaddr, int port, String payload) {
  UDP udp;
  udp.beginPacket(ipaddr, port);
  udp.write(payload);
  udp.endPacket();
}

String* split_string(String str, char c, String* str_array, int len) {
  
  int idx = 0;
  int i = 0;
  for (i = 0; (i < len) && (idx < str.length()); ++i)
  {
    int jdx = arg_list.indexOf(c, idx);
    if (jdx != -1)
    {
      str_array[i] = arg_list.substring(idx,jdx).trim();
      idx = jdx + 1;
    }
    else
    {
      break;
    }
  }
  str_array[i] = nullptr;
  return str_array;
}

void handler(const char* topic, const char* data) {

  String topic_str(topic);
  String data_str(data);

  Serial.println("received " + topic_str + ": " + data);

  if ( topic_str.compareTo(String(NAME_PUBLIC_IP_TOPIC)) == 0 )
  {
    public_ip_str = data_str;
    Particle.publish(NAME_PUBLIC_IP_ADDR, public_ip_str);
    Particle.publish(NAME_LOCAL_IP_ADDR, local_ip_str);
  }
}


