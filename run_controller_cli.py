#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os

from aioconsole import ainput

from joycontrol import logging_default as log, utils
from joycontrol.command_line_interface import ControllerCLI
from joycontrol.controller import Controller
from joycontrol.controller_state import ControllerState, button_push
from joycontrol.memory import FlashMemory
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server

logger = logging.getLogger(__name__)


async def buy(controller_state: ControllerState):
    if controller_state.get_controller() != Controller.PRO_CONTROLLER:
        raise ValueError('This script only works with the Pro Controller!')
    await controller_state.connect()
    await ainput(prompt='动森购买器 Make sure the  Animal crossing in shop and press <enter> to continue.')
    user_input = asyncio.ensure_future(
        ainput(prompt='Buying gifts... Press <enter> to stop.')
    )
    while not user_input.done():
        await button_push(controller_state, 'a')
        await button_push(controller_state, 'b')
        await asyncio.sleep(0.4)
        await button_push(controller_state, 'a')
        await button_push(controller_state, 'b')
        await asyncio.sleep(0.4)
        await button_push(controller_state, 'down')
        await button_push(controller_state, 'a')
        await button_push(controller_state, 'b')
        await asyncio.sleep(1.5)
        await button_push(controller_state, 'a')
        await button_push(controller_state, 'b')
        await asyncio.sleep(0.4)
        await button_push(controller_state, 'a')
        await button_push(controller_state, 'b')
        await asyncio.sleep(0.4)
    await user_input





async def drop(controller_state: ControllerState):
    if controller_state.get_controller() != Controller.PRO_CONTROLLER:
        raise ValueError('This script only works with the Pro Controller!')
    await controller_state.connect()
    await ainput(prompt='动森购买器  and press <enter> to continue.')
    user_input = asyncio.ensure_future(
        ainput(prompt='Buying gifts... Press <enter> to stop.')
    )
    while not user_input.done():
        await button_push(controller_state, 'a')
        await asyncio.sleep(0.3)
        await button_push(controller_state, 'down')
        await button_push(controller_state, 'a')
        await asyncio.sleep(0.8)
        await button_push(controller_state, 'right')
        await asyncio.sleep(0.3)
    await user_input

    
async def test_controller_buttons(controller_state: ControllerState):
    """
    Example controller script.
    Navigates to the "Test Controller Buttons" menu and presses all buttons.
    """
    if controller_state.get_controller() != Controller.PRO_CONTROLLER:
        raise ValueError('This script only works with the Pro Controller!')
    

    # waits until controller is fully connected
    await controller_state.connect()

    await ainput(prompt='Make sure the Switch is in the Home menu and press <enter> to continue.')

    """
    # We assume we are in the "Change Grip/Order" menu of the switch
    await button_push(controller_state, 'home')

    # wait for the animation
    await asyncio.sleep(1)
    """

    # Goto settings
    await button_push(controller_state, 'down', sec=1)
    await button_push(controller_state, 'right', sec=2)
    await asyncio.sleep(0.3)
    await button_push(controller_state, 'left')
    await asyncio.sleep(0.3)
    await button_push(controller_state, 'a')
    await asyncio.sleep(0.3)

    # go all the way down
    await button_push(controller_state, 'down', sec=4)
    await asyncio.sleep(0.3)

    # goto "Controllers and Sensors" menu
    for _ in range(2):
        await button_push(controller_state, 'up')
        await asyncio.sleep(0.3)
    await button_push(controller_state, 'right')
    await asyncio.sleep(0.3)

    # go all the way down
    await button_push(controller_state, 'down', sec=3)
    await asyncio.sleep(0.3)

    # goto "Test Input Devices" menu
    await button_push(controller_state, 'up')
    await asyncio.sleep(0.3)
    await button_push(controller_state, 'a')
    await asyncio.sleep(0.3)

    # goto "Test Controller Buttons" menu
    await button_push(controller_state, 'a')
    await asyncio.sleep(0.3)

    # push all buttons except home and capture
    button_list = controller_state.button_state.get_available_buttons()
    if 'capture' in button_list:
        button_list.remove('capture')
    if 'home' in button_list:
        button_list.remove('home')

    user_input = asyncio.ensure_future(
        ainput(prompt='Pressing all buttons... Press <enter> to stop.')
    )

    # push all buttons consecutively until user input
    while not user_input.done():
        for button in button_list:
            await button_push(controller_state, button)
            await asyncio.sleep(0.1)

            if user_input.done():
                break

    # await future to trigger exceptions in case something went wrong
    await user_input

    # go back to home
    await button_push(controller_state, 'home')


async def set_amiibo(controller_state, file_path):
    """
    Sets nfc content of the controller state to contents of the given file.
    :param controller_state: Emulated controller state
    :param file_path: Path to amiibo dump file
    """
    loop = asyncio.get_event_loop()

    with open(file_path, 'rb') as amiibo_file:
        content = await loop.run_in_executor(None, amiibo_file.read)
        controller_state.set_nfc(content)


async def mash_button(controller_state, button, interval):
    # waits until controller is fully connected
    await controller_state.connect()

    if button not in controller_state.button_state.get_available_buttons():
        raise ValueError(f'Button {button} does not exist on {controller_state.get_controller()}')

    user_input = asyncio.ensure_future(
        ainput(prompt=f'Pressing the {button} button every {interval} seconds... Press <enter> to stop.')
    )
    # push a button repeatedly until user input
    while not user_input.done():
        await button_push(controller_state, button)
        await asyncio.sleep(float(interval))

    # await future to trigger exceptions in case something went wrong
    await user_input


    
    
    
async def _main(args):
    # parse the spi flash
    if args.spi_flash:
        with open(args.spi_flash, 'rb') as spi_flash_file:
            spi_flash = FlashMemory(spi_flash_file.read())
    else:
        # Create memory containing default controller stick calibration
        spi_flash = FlashMemory()

    # Get controller name to emulate from arguments
    controller = Controller.from_arg(args.controller)

    with utils.get_output(path=args.log, default=None) as capture_file:
        factory = controller_protocol_factory(controller, spi_flash=spi_flash)
        ctl_psm, itr_psm = 17, 19
        transport, protocol = await create_hid_server(factory, reconnect_bt_addr=args.reconnect_bt_addr,
                                                      ctl_psm=ctl_psm,
                                                      itr_psm=itr_psm, capture_file=capture_file,
                                                      device_id=args.device_id)

        controller_state = protocol.get_controller_state()

        # Create command line interface and add some extra commands
        cli = ControllerCLI(controller_state)
        '''
        Custom Commands
        '''
        async def _run_drop(): 
            await drop(controller_state)
        cli.add_command('drop',_run_drop)
        
        
        async def _run_buy(): 
            await buy(controller_state)
        cli.add_command('buy',_run_buy)

        # Wrap the script so we can pass the controller state. The doc string will be printed when calling 'help'
        async def _run_test_controller_buttons():
            """
            test_buttons - Navigates to the "Test Controller Buttons" menu and presses all buttons.
            """
            await test_controller_buttons(controller_state)

        # add the script from above
        cli.add_command('test_buttons', _run_test_controller_buttons)
       
        
        # Mash a button command
        async def call_mash_button(*args):
            """
            mash - Mash a specified button at a set interval

            Usage:
                mash <button> <interval>
            """
            if not len(args) == 2:
                raise ValueError('"mash_button" command requires a button and interval as arguments!')

            button, interval = args
            await mash_button(controller_state, button, interval)

        # add the script from above
        cli.add_command('mash', call_mash_button)
        
        # Create Custom Command:
        #async def digwalls(*args):
        #    _set_stick(l, up, 1)
        #    call_mash_button(a)

        # Create amiibo command
        async def amiibo(*args):
            """
            amiibo - Sets nfc content

            Usage:
                amiibo <file_name>          Set controller state NFC content to file
                amiibo remove               Remove NFC content from controller state
            """
            if controller_state.get_controller() == Controller.JOYCON_L:
                raise ValueError('NFC content cannot be set for JOYCON_L')
            elif not args:
                raise ValueError('"amiibo" command requires file path to an nfc dump as argument!')
            elif args[0] == 'remove':
                controller_state.set_nfc(None)
                print('Removed nfc content.')
            else:
                await set_amiibo(controller_state, args[0])

        # add the script from above
        cli.add_command('amiibo', amiibo)

        try:
            await cli.run()
        finally:
            logger.info('Stopping communication...')
            await transport.close()


if __name__ == '__main__':
    # check if root
    if not os.geteuid() == 0:
        raise PermissionError('Script must be run as root!')

    # setup logging
    #log.configure(console_level=logging.ERROR)
    log.configure()

    parser = argparse.ArgumentParser()
    parser.add_argument('controller', help='JOYCON_R, JOYCON_L or PRO_CONTROLLER')
    parser.add_argument('-l', '--log')
    parser.add_argument('-d', '--device_id')
    parser.add_argument('--spi_flash')
    parser.add_argument('-r', '--reconnect_bt_addr', type=str, default=None,
                        help='The Switch console Bluetooth address, for reconnecting as an already paired controller')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _main(args)
    )
