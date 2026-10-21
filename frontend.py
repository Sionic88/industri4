import pygame as pg
import deler
import json

pg.init()


#instillingene
WIDTH = 1600
HEIGHT = 880
GRID_SIZE = 40

#Meny instillinger
MENU_X = 20
MENU_Y = 80
MENU_WIDTH = 220
MENU_ITEM_HIGHT = 45

#bestillingsknapp
SEND_BUTTON_X = 20
SEND_BUTTON_Y = 600
SEND_BUTTON_WIDTH = 220
SEND_BUTTON_HEIGHT = 50

#Robot-gridden
ROBOT_CELL_MM = 60

ROBOT_COLS = 10
ROBOT_ROWS = 8

ROBOT_CELL_PX = 60

start_x = 0
start_y = 0

robot_grid_width = ROBOT_COLS * ROBOT_CELL_PX
robot_grid_height = ROBOT_ROWS * ROBOT_CELL_PX

ROBOT_GRID_X = (WIDTH - robot_grid_width) // 2
ROBOT_GRID_Y = (HEIGHT - robot_grid_height) // 2

#variabel som regner ut origo på skjermen
origin_screen_x = ROBOT_GRID_X + ROBOT_CELL_PX / 2
origin_screen_y = ROBOT_GRID_Y + ROBOT_CELL_PX / 2

#Moduler fra deler.py
module_catalog = deler.modules
placed_modules = []


#ordrefunksjon
def create_order():

    order = {
        "modules": []
    }

    for placed_module in placed_modules:

        robot_col = round(
            (placed_module["x"] - ROBOT_GRID_X) / ROBOT_CELL_PX
        )

        robot_row =  round(
            (placed_module["y"] - ROBOT_GRID_Y) / ROBOT_CELL_PX
        )

        x_mm, y_mm = cell_to_robot_coordinates(
            robot_col,
            robot_row
        )

        module_order = {
            "id": placed_module["id"],
            "x_mm": x_mm,
            "y_mm": y_mm,
            "rotation": placed_module["rotation"]
        }

        order["modules"].append(module_order)
    with open("ordre.json", "w") as file:
        json.dump(order, file, indent=4)

    print ("ordre lagret til ordre.json")

#Funksjoner for å konvertere mellom rutenettkoordinater og robotkoordinater
def cell_to_robot_coordinates(col, row):
    x_mm = col * ROBOT_CELL_MM
    y_mm = row * ROBOT_CELL_MM

    return x_mm, y_mm

def cell_is_available(col, row):

    # Origo er tillatt
    if col == 0 and row == 0:
        return True

    # Øverste rad til høyre for origo er utilgjengelig
    if row == 0:
        return False

    # Venstre kolonne under origo er utilgjengelig
    if col == 0:
        return False

    return True

def draw_send_button():

    send_rect = pg.Rect(
        SEND_BUTTON_X,
        SEND_BUTTON_Y,
        SEND_BUTTON_WIDTH,
        SEND_BUTTON_HEIGHT
    )

    pg.draw.rect(
        screen,
        (180, 220, 180),
        send_rect
    )

    pg.draw.rect(
        screen,
        (60, 100, 60),
        send_rect,
        2
    )

    font = pg.font.SysFont(None, 30)

    text = font.render(
        "SEND ORDRE",
        True,
        (0, 0, 0)
    )

    text_rect = text.get_rect(
        center=send_rect.center
    )

    screen.blit(text, text_rect)

def draw_module_menu():
    pg.draw.rect(
        screen,
        (235, 235, 240),
        (
            MENU_X - 10,
            MENU_Y - 20,
            MENU_WIDTH + 20,
            500
        )
    )

    y = MENU_Y

    for module_id, module_data in module_catalog.items():

        button_rect = pg.Rect(
            MENU_X,
            y,
            MENU_WIDTH,
            MENU_ITEM_HIGHT
        )

        pg.draw.rect(
            screen,
            (220, 220, 220),
            button_rect,
            2
        )

        font = pg.font.SysFont(None, 28)

        text = font.render(
            module_data["name"],
            True,
            (0, 0, 0)
        )

        screen.blit(
            text,
            (
                MENU_X + 10,
                y + 10
            )
        )

        y +=MENU_ITEM_HIGHT + 10


def module_can_be_placed(start_col, start_row, width_cells, hight_cells, current_module):

    #Sjekk at modul ikke går utenfor rutenettet
    if start_col < 0 or start_row < 0:
        return False


    if start_col + width_cells > ROBOT_COLS:
        return False

    if start_row + hight_cells > ROBOT_ROWS:
        return False

    #sjekk hver celle som modulen dekker
    for col in range(start_col, start_col + width_cells):
        for row in range(start_row, start_row + hight_cells):

            if not cell_is_available(col, row):
                return False

    new_rect = pg.Rect (
        start_col,
        start_row,
        width_cells,
        hight_cells
    )

    for placed_module in placed_modules:

        #ikke sjekke modulen mot seg selv
        if placed_module is current_module:
            continue   

        module_data = module_catalog[placed_module["id"]]

        if placed_module["rotation"] in (0, 180):
            other_width = int(module_data["width_mm"] / ROBOT_CELL_MM)
            other_height = int(module_data["height_mm"] / ROBOT_CELL_MM)
        else:
            other_width = int(module_data["height_mm"] / ROBOT_CELL_MM)
            other_height = int(module_data["width_mm"] / ROBOT_CELL_MM)

        other_col = round(
            (placed_module["x"] - ROBOT_GRID_X) / ROBOT_CELL_PX
        )

        other_row = round(
            (placed_module["y"] - ROBOT_GRID_Y) / ROBOT_CELL_PX
        )

        other_rect = pg.Rect(
            other_col,
            other_row,
            other_width,
            other_height
        )

        if new_rect.colliderect(other_rect):
            return False
    
    return True

    

def draw_robot_grid():

    # Bakgrunn
    pg.draw.rect(
        screen,
        (225, 235, 225),
        (
            ROBOT_GRID_X,
            ROBOT_GRID_Y,
            robot_grid_width,
            robot_grid_height
        )
    )

    # Vertikale linjer
    for col in range(ROBOT_COLS + 1):
        x = ROBOT_GRID_X + col * ROBOT_CELL_PX

        pg.draw.line(
            screen,
            (80, 80, 80),
            (x, ROBOT_GRID_Y),
            (x, ROBOT_GRID_Y + robot_grid_height),
            2
        )

    # Horisontale linjer
    for row in range(ROBOT_ROWS + 1):
        y = ROBOT_GRID_Y + row * ROBOT_CELL_PX

        pg.draw.line(
            screen,
            (80, 80, 80),
            (ROBOT_GRID_X, y),
            (ROBOT_GRID_X + robot_grid_width, y),
            2
        )

def add_module(module_id):

    module_data = module_catalog[module_id]

    new_module = {
        "id": module_id,
        "x": 300,
        "y": 100,
        "rotation": 0
    }

    placed_modules.append(new_module)

screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Modulkonfigurator")

clock = pg.time.Clock()


#dra og dropp variabler
dragging = False
drag_offset_x = 0
drag_offset_y = 0
selected_module = None

running = True

while running:




    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_r and selected_module is not None:
                selected_module["rotation"] = (
                    selected_module["rotation"] + 90

                ) % 360



        elif event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:  # Venstre museknapp

                mouse_x, mouse_y = event.pos

                send_rect = pg.Rect(
                    SEND_BUTTON_X,
                    SEND_BUTTON_Y,
                    SEND_BUTTON_WIDTH,
                    SEND_BUTTON_HEIGHT
                )

                if send_rect.collidepoint(mouse_x, mouse_y):
                    create_order()
                    continue

                menu_clicked = False
                menu_y = MENU_Y

                for module_id, module_data in module_catalog.items():

                    button_rect = pg.Rect(
                        MENU_X,
                        menu_y,
                        MENU_WIDTH,
                        MENU_ITEM_HIGHT
                    )

                    if button_rect.collidepoint(mouse_x, mouse_y):
                        add_module(module_id)
                        menu_clicked = True
                        break

                    menu_y += MENU_ITEM_HIGHT + 10

                if menu_clicked:
                    continue

                for placed_module in placed_modules:

                    module_data = module_catalog[placed_module["id"]]
                    
                    if placed_module["rotation"] in (0, 180):
                        module_width = module_data["width_mm"] / ROBOT_CELL_MM
                        module_height = module_data["height_mm"] / ROBOT_CELL_MM
                    else:
                        module_width = module_data["height_mm"] / ROBOT_CELL_MM
                        module_height = module_data["width_mm"] / ROBOT_CELL_MM

                    module_width_px = module_width * ROBOT_CELL_PX
                    module_height_px = module_height * ROBOT_CELL_PX

                    module_rect = pg.Rect(
                        placed_module["x"],
                        placed_module["y"],
                        module_width_px,
                        module_height_px
                    )

                    #sjekke om kunden klikker på modulen
                    if module_rect.collidepoint(mouse_x, mouse_y):
                        selected_module = placed_module
                        dragging = True

                        start_x = selected_module["x"]
                        start_y = selected_module["y"]

                        #huske hvor på modulen kunden klikket
                        drag_offset_x = mouse_x - module_rect.x
                        drag_offset_y = mouse_y - module_rect.y

                        break

            if event.button == 3: #høreklikk

                mouse_x, mouse_y = event.pos

                for placed_module in placed_modules:

                    module_data = module_catalog[placed_module["id"]]

                    if placed_module["rotation"] in (0, 180):
                        module_width = module_data["width_mm"] / ROBOT_CELL_MM
                        module_height = module_data["height_mm"] / ROBOT_CELL_MM

                    else:
                        module_width = module_data["height_mm"] / ROBOT_CELL_MM
                        module_height = module_data["width_mm"] / ROBOT_CELL_MM

                    module_width_px = module_width * ROBOT_CELL_PX
                    module_height_px = module_height * ROBOT_CELL_PX

                    module_rect = pg.Rect(
                        placed_module["x"],
                        placed_module["y"],
                        module_width_px,
                        module_height_px
                    )

                    if module_rect.collidepoint(mouse_x, mouse_y):
                        placed_modules.remove(placed_module)
                        print("removed module")
                        break


        elif event.type == pg.MOUSEMOTION:
            if dragging and selected_module is not None:
                mouse_x, mouse_y = event.pos

                selected_module["x"] = mouse_x - drag_offset_x
                selected_module["y"] = mouse_y - drag_offset_y

        #Når mueknappen slippes, stoppe dra og dropp
        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1 and dragging and selected_module is not None:
                dragging = False

                #snap modulen til nærmeste rutenettposisjon
                #module_x = round(module_x)
                #module_y = round(module_y)
                if (
                    ROBOT_GRID_X <= selected_module["x"] <= ROBOT_GRID_X + robot_grid_width
                    and
                    ROBOT_GRID_Y <= selected_module["y"] <= ROBOT_GRID_Y + robot_grid_height
                ):
                    #Finn nærmeste kolonne og rad i robot gridet.
                    robot_col = round(
                        (selected_module["x"] - ROBOT_GRID_X) / ROBOT_CELL_PX
                    )

                    robot_row = round(
                        (selected_module["y"] - ROBOT_GRID_Y) / ROBOT_CELL_PX
                    )


                    module_data = module_catalog[selected_module["id"]]

                    if selected_module["rotation"] in (0, 180):
                        module_width = module_data["width_mm"] / ROBOT_CELL_MM
                        module_height = module_data["height_mm"] / ROBOT_CELL_MM
                    else:
                        module_width = module_data["height_mm"] / ROBOT_CELL_MM
                        module_height = module_data["width_mm"] / ROBOT_CELL_MM

                    if module_can_be_placed(
                        robot_col,
                        robot_row,
                        int(module_width),
                        int(module_height),
                        selected_module
                    ):
                        #snap modulen til nøyaktig robot rutenettposisjon 
                        selected_module["x"] = ROBOT_GRID_X + robot_col * ROBOT_CELL_PX
                        selected_module["y"] = ROBOT_GRID_Y + robot_row * ROBOT_CELL_PX

                        #regn ut robotkoordinater i mm
                        robot_x_mm, robot_y_mm = cell_to_robot_coordinates(
                            robot_col,
                            robot_row
                        )

                        print(
                            "robot posisjon (mm):", 
                            robot_x_mm,
                            robot_y_mm,
                            "Rotasjon (grader):",
                            selected_module["rotation"]
                        )
                    else:
                        print("Modulen kan ikke plasseres der.")
                        selected_module["x"] = start_x
                        selected_module["y"] = start_y
                        selected_module = None
                else:
                    selected_module["x"] = start_x
                    selected_module["y"] = start_y
                    selected_module = None
          

    #Bakgrunnsfarge
    screen.fill((245, 245, 245))

    # Tegn rutenettet
    for x in range(0, WIDTH, GRID_SIZE):
        pg.draw.line(screen, (200, 200, 200), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, GRID_SIZE):
        pg.draw.line(screen, (200, 200, 200), (0, y), (WIDTH, y))

    #tegn robotgridden
    draw_robot_grid()
    pg.draw.circle(
        screen,
        (255, 0, 0),
        (int(origin_screen_x), int(origin_screen_y)),
        8
    )

    #tegn menyen
    draw_module_menu()
    draw_send_button()


    # Tegn modulen
    for placed_module in placed_modules:

        module_data = module_catalog[placed_module["id"]]

        if placed_module["rotation"] in (0, 180):
            module_width = module_data["width_mm"] / ROBOT_CELL_MM
            module_height = module_data["height_mm"] / ROBOT_CELL_MM
        else:
            module_width = module_data["height_mm"] / ROBOT_CELL_MM
            module_height = module_data["width_mm"] / ROBOT_CELL_MM

        module_width_px = module_width * ROBOT_CELL_PX
        module_height_px = module_height * ROBOT_CELL_PX

        pg.draw.rect(
            screen,
            module_data["color"],
            (
                placed_module["x"],
                placed_module["y"],
                module_width_px,
                module_height_px
            )
        )

        module_image = pg.image.load(module_data["image"]).convert_alpha()


        if placed_module["rotation"] != 0:
            module_image = pg.transform.rotate(
                module_image,
                -placed_module["rotation"]
            )

        module_image = pg.transform.scale(
            module_image,
            (int(module_width_px), int(module_height_px))
        )


        #finne modulens rektangel
        module_rect = pg.Rect(
            placed_module["x"], 
            placed_module["y"], 
            module_width_px,
            module_height_px
        )        

        image_rect = module_image.get_rect(center=module_rect.center)



        screen.blit(
            module_image,
            image_rect
        )
            



    # Oppdater skjermen

    pg.display.flip()
    clock.tick(60)
pg.quit()