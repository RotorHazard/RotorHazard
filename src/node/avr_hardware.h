#include "config.h"
#include "hardware.h"
#include "commands.h"
#include <Wire.h>
#include "rheeprom.h"

#define SERIAL_BAUD_RATE 115200

#define COMMS_MONITOR_TIME_MS 5000 //I2C communications monitor grace/trigger time

#define EEPROM_ADRW_RXFREQ 0       //address for stored RX frequency value
#define EEPROM_ADRW_ENTERAT 2      //address for stored 'enterAtLevel'
#define EEPROM_ADRW_EXITAT 4       //address for stored 'exitAtLevel'
#define EEPROM_ADRW_EXPIRE 6       //address for stored catch history expire duration
#define EEPROM_ADRW_CHECKWORD 8    //address for integrity-check value
#define EEPROM_CHECK_VALUE 0x3526  //EEPROM integrity-check value
#define EEPROM_SETTINGS_SIZE 16

// Defines for fast ADC reads
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))

void i2cReceive(int byteCount);
bool i2cReadAndValidateIoBuffer(byte expectedSize);
void i2cTransmit();

class AvrHardware : public Hardware {
private:
    // i2c address for node
    // Node 1 = 8, Node 2 = 10, Node 3 = 12, Node 4 = 14
    // Node 5 = 16, Node 6 = 18, Node 7 = 20, Node 8 = 22
    uint8_t i2cAddress = 6 + (NODE_NUMBER * 2);
    bool i2cMonitorEnabledFlag = false;
    mtime_t i2cMonitorLastResetTime = 0;

#if (!defined(NODE_NUMBER)) || (!NODE_NUMBER)
    // Configure the I2C address based on input-pin level.
    void configI2cAddress()
    {
        // current hardware selection
        pinMode(HARDWARE_SELECT_PIN_1, INPUT_PULLUP);
        pinMode(HARDWARE_SELECT_PIN_2, INPUT_PULLUP);
        pinMode(HARDWARE_SELECT_PIN_3, INPUT_PULLUP);
        // legacy selection - DEPRECATED
        pinMode(LEGACY_HARDWARE_SELECT_PIN_1, INPUT_PULLUP);
        pinMode(LEGACY_HARDWARE_SELECT_PIN_2, INPUT_PULLUP);
        pinMode(LEGACY_HARDWARE_SELECT_PIN_3, INPUT_PULLUP);
        pinMode(LEGACY_HARDWARE_SELECT_PIN_4, INPUT_PULLUP);
        pinMode(LEGACY_HARDWARE_SELECT_PIN_5, INPUT_PULLUP);

        delay(100);  // delay a bit a let pin levels settle before reading inputs

        // check if legacy spec pins are in use (2-5 only)
        if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW ||
            digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW ||
            digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW ||
            digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
        {
            // legacy spec
            if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_1) == HIGH)
            {
                if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW)
                    i2cAddress = 8;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW)
                    i2cAddress = 10;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW)
                    i2cAddress = 12;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
                    i2cAddress = 14;
            }
            else
            {
                if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_2) == LOW)
                    i2cAddress = 16;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_3) == LOW)
                    i2cAddress = 18;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_4) == LOW)
                    i2cAddress = 20;
                else if (digitalRead(LEGACY_HARDWARE_SELECT_PIN_5) == LOW)
                    i2cAddress = 22;
            }
        }
        else
        {   // use standard selection
            i2cAddress = 0;
            if (digitalRead(HARDWARE_SELECT_PIN_1) == LOW)
                i2cAddress |= 1;
            if (digitalRead(HARDWARE_SELECT_PIN_2) == LOW)
                i2cAddress |= 2;
            if (digitalRead(HARDWARE_SELECT_PIN_3) == LOW)
                i2cAddress |= 4;
            i2cAddress = 8 + (i2cAddress * 2);
        }
    }
#endif  // (!defined(NODE_NUMBER)) || (!NODE_NUMBER)

    void i2cInitialize(bool delayFlag)
    {
        setStatusLed(true);
        Wire.end();  // release I2C pins (SDA & SCL), in case they are "stuck"
        if (delayFlag)   // do delay if called via comms monitor
            delay(250);  //  to help bus reset and show longer LED flash
        setStatusLed(false);

        Wire.begin(i2cAddress);  // I2C address setup
        Wire.onReceive(i2cReceive);   // Trigger 'i2cReceive' function on incoming data
        Wire.onRequest(i2cTransmit);  // Trigger 'i2cTransmit' function for outgoing data, on master request

        TWAR = (i2cAddress << 1) | 1;  // enable broadcasts to be received
    }

public:
    AvrHardware() : Hardware(HIGH,LOW) {
    }
    void init()
    {
        Hardware::init();

        // init pin used to reset paired Arduino via RESET_PAIRED_NODE command
        pinMode(NODE_RESET_PIN, INPUT_PULLUP);

        // init pin that can be pulled low (to GND) to disable serial port
        pinMode(DISABLE_SERIAL_PIN, INPUT_PULLUP);

    #if (!defined(NODE_NUMBER)) || (!NODE_NUMBER)
        configI2cAddress();
    #else
        delay(100);  // delay a bit a let pin level settle before reading input
    #endif

        if (digitalRead(DISABLE_SERIAL_PIN) == HIGH)
        {
            Serial.begin(SERIAL_BAUD_RATE);  // Start serial interface
            while (!Serial) {
                delay(1);  // Wait for the Serial port to initialize
            }
        }

        i2cInitialize(false);  // setup I2C slave address and callbacks

        // set ADC prescaler to 16 to speedup ADC readings
        sbi(ADCSRA, ADPS2);
        cbi(ADCSRA, ADPS1);
        cbi(ADCSRA, ADPS0);
    }

    void initSettings(uint_fast8_t nIdx, Settings& settings)
    {
        int offset = nIdx*EEPROM_SETTINGS_SIZE;
        if (eepromReadWord(offset + EEPROM_ADRW_CHECKWORD) == EEPROM_CHECK_VALUE)
        {
            settings.vtxFreq = eepromReadWord(offset + EEPROM_ADRW_RXFREQ);
            settings.enterAtLevel = eepromReadWord(offset + EEPROM_ADRW_ENTERAT);
            settings.exitAtLevel = eepromReadWord(offset + EEPROM_ADRW_EXITAT);
        }
        else
        {    // if no match then initialize EEPROM values
            eepromWriteWord(offset + EEPROM_ADRW_RXFREQ, settings.vtxFreq);
            eepromWriteWord(offset + EEPROM_ADRW_ENTERAT, settings.enterAtLevel);
            eepromWriteWord(offset + EEPROM_ADRW_EXITAT, settings.exitAtLevel);
            eepromWriteWord(offset + EEPROM_ADRW_CHECKWORD, EEPROM_CHECK_VALUE);
        }
    }

    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        uint16_t dataPin = RX5808_DATA_PIN;  //DATA (CH1) output line to RX5808 module
        uint16_t clkPin = RX5808_CLK_PIN;    //SEL (CH2) output line to RX5808 module
        uint16_t selPin = RX5808_SEL_PIN;    //CLK (CH3) output line to RX5808 module
        uint16_t rssiPin = RSSI_INPUT_PIN;   //RSSI input from RX5808
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }

    void processStatusFlags(const mtime_t ms, const uint8_t statusFlags) {
        bool anyNodeActive = false;
        for (int_fast8_t i=rssiRxs.getCount()-1; i>=0; i--) {
            RssiNode& node = rssiRxs.getRssiNode(i);
            if (node.active) {
                anyNodeActive = true;
                break;
            }
        }

        if (anyNodeActive)
        {
            if (i2cMonitorEnabledFlag)
            {
                if ((statusFlags & COMM_ACTIVITY) && (statusFlags & SERIAL_CMD_MSG) == 0)
                {  //I2C communications activity detected; update comms monitor time
                    i2cMonitorLastResetTime = ms;
                }
                else if (ms - i2cMonitorLastResetTime > COMMS_MONITOR_TIME_MS)
                {  //too long since last communications activity detected
                    i2cMonitorEnabledFlag = false;
                    // redo init, which should release I2C pins (SDA & SCL) if "stuck"
                    i2cInitialize(true);
                }
            }
            else if ((statusFlags & POLLING) &&
                    (statusFlags & SERIAL_CMD_MSG) == 0)
            {  //if activated and I2C POLLING cmd received then enable comms monitor
                i2cMonitorEnabledFlag = true;
                i2cMonitorLastResetTime = ms;
            }
        }
        else if (i2cMonitorEnabledFlag)
        {
            i2cMonitorEnabledFlag = false;
        }
    }

    // Node reset for ISP; resets other node wired to this node's reset pin
    void resetPairedNode(bool pinState)
    {
        if (pinState)
        {
            pinMode(NODE_RESET_PIN, INPUT_PULLUP);
        }
        else
        {
            pinMode(NODE_RESET_PIN, OUTPUT);
            digitalWrite(NODE_RESET_PIN, LOW);
        }
    }

    void doJumpToBootloader()
    {
    }

    uint8_t getAddress()
    {
        return i2cAddress;
    }

    void storeFrequency(freq_t freq)
    {
        eepromWriteWord(EEPROM_ADRW_RXFREQ, freq);
    }

    void storeEnterAtLevel(rssi_t rssi)
    {
        eepromWriteWord(EEPROM_ADRW_ENTERAT, rssi);
    }

    void storeExitAtLevel(rssi_t rssi)
    {
        eepromWriteWord(EEPROM_ADRW_EXITAT, rssi);
    }
};
