#include "config.h"
#include "hardware.h"
#include "commands.h"

#define SERIAL_BAUD_RATE 921600

#if STM32_SERIALUSB_FLAG
#define SERIALCOM SerialUSB
#else
#define SERIALCOM Serial
#endif

// address for STM32 bootloader
#if defined(STM32F1)
#define BOOTLOADER_ADDRESS 0x1FFFF000
#else
#define BOOTLOADER_ADDRESS 0x1FFF0000
#endif

class Stm32Hardware : public Hardware {
private:
    int rx5808SelPinForNodeIndex(int nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return PB7;
            case 1:
                return PB8;
            case 2:
                return PB9;
            case 3:
                return PB12;
            case 4:
                return PB13;
            case 5:
                return PB14;
            case 6:
                return PB15;
            default:
                return PB6;
        }
    }

    int rssiInputPinForNodeIndex(int nIdx)
    {
        switch (nIdx)
        {
            case 0:
                return A1;
            case 1:
                return A2;
            case 2:
                return A3;
            case 3:
                return A4;
            case 4:
                return A5;
            case 5:
                return A6;
            case 6:
                return A7;
            default:
                return A0;
        }
    }

public:
    Stm32Hardware() : Hardware(LOW,HIGH) {
    }
    void init()
    {
        Hardware::init();

        SERIALCOM.begin(SERIAL_BAUD_RATE);  // Start serial interface
        while (!SERIALCOM) {
            delay(1);  // Wait for the Serial port to initialize
        }
    }

    void initRxModule(int nIdx, RxModule& rx)
    {
        uint16_t dataPin = PB3;  //DATA (CH1) output line to (all) RX5808 modules
        uint16_t clkPin = PB4;   //CLK (CH3) output line to (all) RX5808 modules
        uint16_t selPin = rx5808SelPinForNodeIndex(nIdx);  //SEL (CH2) output line to RX5808 module
        uint16_t rssiPin = rssiInputPinForNodeIndex(nIdx); //RSSI input from RX5808
        rx.init(dataPin, clkPin, selPin, rssiPin);
    }

    uint16_t getFeatureFlags() {
        return RHFEAT_STM32_MODE | RHFEAT_JUMPTO_BOOTLDR | RHFEAT_IAP_FIRMWARE;
    }

    // Jump to STM32 built-in bootloader; based on code from
    //  https://stm32f4-discovery.net/2017/04/tutorial-jump-system-memory-software-stm32
    void doJumpToBootloader()
    {
        volatile uint32_t addr = BOOTLOADER_ADDRESS;  // STM32 built-in bootloader address
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

Stm32Hardware defaultHardware;
Hardware *hardware = &defaultHardware;

static Message serialMessage(RssiReceivers::rssiRxs, hardware);

void serialEvent()
{
    handleStreamEvent(SERIALCOM, serialMessage);
}
