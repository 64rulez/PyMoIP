# PyMoIP
Python "Modem over IP" for Minitel

The aim of this project is to try to provide a technical alternative to VoIP in order to allow the usage of French Minitel terminals in this modern era where PSTN technology is disapearing in the entire planet.

As VoIP seems to be the natural replacement to classical PSTN transport, many drawbacks observed (mostly related to quality and stability of the V23 link) make think that this solution is not acceptable. Regular FAX transport have been adapted to IP with T38 and is now well supported. Regular modem transport have been adapted to IP with V150.1 but this approach remains unreachable to normal people due to the ultra high cost of the hardware available.

The main idea, inspired by V150.1, is to only transport over IP the required data and not the "sound of data". Several usages are to be considerated :
- When acting as a user :
  - Use any Linux-box (such as a RPi) to initiate a WebSocket session and insure all required translations and adaptations
  - The Minitel terminal may be directly connected to the Linux-box thru a simple (modified to support 5V TTL) USB-FTDI adapter
  - The Minitel terminal may be indirectly connected to the Linux-box thru a regular USB-Serial adapter and a V23 compatible Hayes modem. This setup requires a minimal phantom PSTN line but might be necessary to allow the usage of Minitel terminals not equiped with peri-informatique connector.
- When acting as a server :
  - Use any computer to accept WebSocket session
  - Yellow Pages reference (used when acting as a user) are available there : http://teletel.org/minitel-yp.json
  - [Planned] Same hardware setup as when "acting as a user" - needs to find a solution for "virtual ring detection"
    This solution is required to allow simple micro-server BBS setup running on vintage real hardware
    
Current implementation allows only "acting as a user" mode, with both direct and indirect connected Minitel terminal. The WebSocket server might be known in Yellow Pages reference or fully selected at the provided requestor. It needs the use of an updated version of Zigazou's PyMinitel library forked here.
