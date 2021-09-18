#include "config.h"
#include "hardware.h"
#include "commands.h"

#define SERIAL_BAUD_RATE 921600

#define SERIALCOM Serial

// address for STM32 bootloader
#if VARIANT == STM32F1_VARIANT
#define BOOTLOADER_ADDRESS 0x1FFFF000
#else
#define BOOTLOADER_ADDRESS 0x1FFF0000
#endif

class Stm32Hardware : public Hardware {
private:
    uint8_t rx5808SelPinForNodeIndex(uint_fast8_t nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return RX5808_SEL0_PIN;
            case 1:
                return RX5808_SEL1_PIN;
            case 2:
                return RX5808_SEL2_PIN;
            case 3:
                return RX5808_SEL3_PIN;
            case 4:
                return RX5808_SEL4_PIN;
            case 5:
                return RX5808_SEL5_PIN;
            case 6:
                return RX5808_SEL6_PIN;
            case 7:
                return RX5808_SEL7_PIN;
            default:
                return RX5808_SEL0_PIN;
        }
    }

    uint8_t rssiInputPinForNodeIndex(uint_fast8_t nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return RSSI_INPUT0_PIN;
            case 1:
                return RSSI_INPUT1_PIN;
            case 2:
                return RSSI_INPUT2_PIN;
            case 3:
                return RSSI_INPUT3_PIN;
            case 4:
                return RSSI_INPUT4_PIN;
            case 5:
                return RSSI_INPUT5_PIN;
            case 6:
                return RSSI_INPUT6_PIN;
            case 7:
                return RSSI_INPUT7_PIN;
            default:
                return RSSI_INPUT0_PIN;
        }
    }

public:
    Stm32Hardware() : Hardware(LOW,HIGH) {
    }
    void init()
    {
        Hardware::init();

        // turn-off all SPI chip selects
        for (uint_fast8_t i=0; i<RX5808_SEL_PIN_COUNT; i++) {
            uint8_t selPin = rx5808SelPinForNodeIndex(i);
            pinMode(selPin, OUTPUT);
            digitalWrite(selPin, HIGH);
        }

        SERIALCOM.begin(SERIAL_BAUD_RATE);  // Start serial interface
        while (!SERIALCOM) {
            delay(1);  // Wait for the Serial port to initialize
        }
    }

    void initRxModule(uint_fast8_t nIdx, RxModule& rx)
    {
        uint8_t dataPin = PB3;  //DATA (CH1) output line to (all) RX5808 modules
        uint8_t clkPin = PB4;   //CLK (CH3) output line to (all) RX5808 modules
        uint8_t selPin = rx5808SelPinForNodeIndex(nIdx);  //SEL (CH2) output line to RX5808 module
        uint8_t rssiPin = rssiInputPinForNodeIndex(nIdx); //RSSI input from RX5808
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }

    const char* getProcessorType() {
#if VARIANT == STM32F1_VARIANT
      return "STM32F1";
#elif VARIANT == STM32F4_VARIANT
      return "STM32F4";
#endif
    }

    uint16_t getFeatureFlags() {
        return Hardware::getFeatureFlags() | RHFEAT_STM32_MODE | RHFEAT_JUMPTO_BOOTLDR | RHFEAT_IAP_FIRMWARE;
    }

    // Jump to STM32 built-in bootloader; based on code from
    //  https://stm32f4-discovery.net/2017/04/tutorial-jump-system-memory-software-stm32
    void doJumpToBootloader()
    {
        uint32_t addr = BOOTLOADER_ADDRESS;  // STM32 built-in bootloader address
        void (*SysMemBootJump)(void);

        SERIALCOM.flush();  // flush and close down serial port
        SERIALCOM.end();

        // disable RCC, set it to default (after reset) settings; internal clock, no PLL, etc.
    #if defined(USE_HAL_DRIVER)
        HAL_RCC_DeInit();
    #endif /* defined(USE_HAL_DRIVER) */
    #if defined(USE_STDPERIPH_DRIVER)
        RCC_DeInit();
    #endif /* defined(USE_STDPERIPH_DRIVER) */

        // disable systick timer and reset it to default values
        SysTick->CTRL = 0;
        SysTick->LOAD = 0;
        SysTick->VAL = 0;

        __disable_irq();  // disable all interrupts

        // Remap system memory to address 0x0000 0000 in address space
        // For each family registers may be different.
        // Check reference manual for each family.
        // For STM32F4xx, MEMRMP register in SYSCFG is used (bits[1:0])
        // For STM32F0xx, CFGR1 register in SYSCFG is used (bits[1:0])
        // For others, check family reference manual
    #if defined(STM32F4)
        SYSCFG->MEMRMP = 0x01;
    #endif
    #if defined(STM32F0)
        SYSCFG->CFGR1 = 0x01;
    #endif

         //Set jump memory location for system memory
         // Use address with 4 bytes offset which specifies jump location where program starts
        SysMemBootJump = (void (*)(void)) (*((uint32_t *)(addr + 4)));

        // Set main stack pointer
        // (This step must be done last otherwise local variables in this function
        // don't have proper value since stack pointer is located on different position
        // Set direct address location which specifies stack pointer in SRAM location)
        __set_MSP(*(uint32_t *)addr);  // @suppress("Invalid arguments")

        SysMemBootJump();  // do jump to bootloader in system memory
    }
};
