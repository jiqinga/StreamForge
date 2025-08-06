from loguru import logger

from app.core.crud import CRUDBase
from app.models.system import Button, Menu
from app.schemas.menus import ButtonBase, MenuCreate, MenuUpdate


class MenuController(CRUDBase[Menu, MenuCreate, MenuUpdate]):
    def __init__(self):
        super().__init__(model=Menu)

    async def get_by_menu_name(self, menu_name: str) -> Menu | None:
        return await self.model.filter(menu_name=menu_name).first()

    async def get_by_route_path(self, route_path: str) -> Menu | None:
        return await self.model.filter(route_path=route_path).first()

    async def get_by_id_list(self, id_list: list[int] | str) -> list[Menu] | None:
        if isinstance(id_list, str):
            id_list = id_list.split(",")
        return await self.model.filter(id__in=id_list)

    @staticmethod
    async def update_buttons_by_code(menu: Menu, buttons: list[ButtonBase] | None = None) -> bool:
        if not buttons:
            return False

        existing_buttons = [button.button_code for button in await menu.by_menu_buttons]

        menu_buttons = [button.button_code for button in buttons]

        for button_code in set(existing_buttons) - set(menu_buttons):
            logger.error(f"Button Deleted {button_code}")
            await Button.filter(button_code=button_code).delete()

        await menu.by_menu_buttons.clear()
        for button in buttons:
            button_obj, _ = await Button.update_or_create(button_code=button.button_code, defaults=dict(button_desc=button.button_desc))
            await menu.by_menu_buttons.add(button_obj)

        return True
        
    async def remove(self, **kwargs) -> None:
        """
        增强的菜单删除方法，处理以下情况：
        1. 递归删除子菜单
        2. 清除菜单按钮关联
        3. 清除角色菜单关联
        4. 清除激活菜单引用
        """
        menu = await self.model.get(**kwargs)
        
        if not menu:
            return
            
        # 1. 查找并递归删除所有子菜单
        child_menus = await self.model.filter(parent_id=menu.id)
        for child_menu in child_menus:
            await self.remove(id=child_menu.id)
            
        # 2. 清除菜单按钮关联
        await menu.by_menu_buttons.clear()
        
        # 3. 清除角色菜单关联
        await menu.by_menu_roles.clear()
        
        # 4. 清除将此菜单作为激活菜单的引用
        menus_with_active = await self.model.filter(active_menu_id=menu.id)
        for m in menus_with_active:
            m.active_menu = None
            await m.save()
            
        # 5. 删除菜单本身
        await menu.delete()


menu_controller = MenuController()
