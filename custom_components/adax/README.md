# Adax


Not tested much, so all feedback is welcome


Custom component for using Adax in Home Assistant

## Install
Copy the files to the custom_components folder in Home Assistant config.

In configuration.yaml:

```
climate:
  - platform: adax
    client_id: "112395"  # replace with your client ID (see Adax WiFi app, Account Section)
    client_secret: "6imtpX63D5WoRyKh"  # replace with your client SECRET (see Adax WiFi app, Account Section)
```

API details: https://adax.no/om-adax/api-development/

[Buy me a coffee :)](http://paypal.me/dahoiv)
