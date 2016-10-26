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

int get_public_ip(String s)
{
  Serial.println("Requesting public ip");
  bool result = Particle.publish(NAME_PUBLIC_IP_TOPIC);
  return (result == true) ? 1 : 0;
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


