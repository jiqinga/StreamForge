from fastapi import APIRouter, Query
from tortoise.functions import Count

from app.api.v1.utils import insert_log
from app.controllers.menu import menu_controller
from app.models.system import LogType, LogDetailType, IconType
from app.models.system import Menu
from app.schemas.base import Success, SuccessExtra
from app.schemas.menus import MenuCreate, MenuUpdate

router = APIRouter()


async def build_menu_tree(menus: list[Menu], parent_id: int = 0, simple: bool = False) -> list[dict]:
    """
    递归生成菜单树
    :param menus:
    :param parent_id:
    :param simple: 是否简化返回数据
    :return:
    """
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = await build_menu_tree(menus, menu.id, simple)
            if simple:
                menu_dict = {"id": menu.id, "label": menu.menu_name, "pId": menu.parent_id}
            else:
                menu_dict = await menu.to_dict()
                if menu.icon_type == IconType.local:
                    menu_dict["localIcon"] = menu.icon
                    menu_dict.pop("icon")
                menu_dict["buttons"] = [await button.to_dict() for button in await menu.by_menu_buttons]
            if children:
                menu_dict["children"] = children
            tree.append(menu_dict)
    return tree


@router.get("/menus", summary="查看用户菜单")
async def _(current: int = Query(1, description="页码"), size: int = Query(100, description="每页数量")):
    total, menus = await menu_controller.list(page=current, page_size=size, order=["id"])
    # 递归生成菜单
    menu_tree = await build_menu_tree(menus, simple=False)
    data = {"records": menu_tree}
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuGetList, by_user_id=0)
    return SuccessExtra(data=data, total=total, current=current, size=size)


@router.get("/menus/tree/", summary="查看菜单树")
async def _():
    menus = await Menu.filter(constant=False)
    # 递归生成菜单
    menu_tree = await build_menu_tree(menus, simple=True)
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuGetTree, by_user_id=0)
    return Success(data=menu_tree)


@router.get("/menus/{menu_id}", summary="查看菜单")
async def get_menu(menu_id: int):
    menu_obj: Menu = await menu_controller.get(id=menu_id)
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuGetOne, by_user_id=0)
    return Success(data=await menu_obj.to_dict())


@router.post("/menus", summary="创建菜单")
async def _(menu_in: MenuCreate):
    is_exist = await menu_controller.model.exists(route_path=menu_in.route_path)
    if is_exist:
        return Success(
            code="4090", msg=f"The menu with this route_path {menu_in.route_path} already exists in the system."
        )

    if menu_in.active_menu:
        menu_in.active_menu = await menu_controller.get(menu_name=menu_in.active_menu)

    new_menu = await menu_controller.create(obj_in=menu_in, exclude={"buttons"})
    if new_menu and menu_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(new_menu, menu_in.by_menu_buttons)
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuCreateOne, by_user_id=0)
    return Success(msg="Created Successfully", data={"created_id": new_menu.id})


@router.patch("/menus/{menu_id}", summary="更新菜单")
async def _(menu_id: int, menu_in: MenuUpdate):
    menu_obj = await menu_controller.update(id=menu_id, obj_in=menu_in, exclude={"buttons"})
    if menu_obj and menu_in.by_menu_buttons:
        await menu_controller.update_buttons_by_code(menu_obj, menu_in.by_menu_buttons)
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuUpdateOne, by_user_id=0)
    return Success(msg="Updated Successfully", data={"updated_id": menu_id})


@router.delete("/menus/{menu_id}", summary="删除菜单")
async def _(menu_id: int):
    await menu_controller.remove(id=menu_id)
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuDeleteOne, by_user_id=0)
    return Success(msg="Deleted Successfully", data={"deleted_id": menu_id})


@router.delete("/menus", summary="批量删除菜单")
async def _(ids: str = Query(description="菜单ID列表, 用逗号隔开")):
    menu_ids = ids.split(",")
    for menu_id in menu_ids:
        await menu_controller.remove(id=int(menu_id))
    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuBatchDeleteOne, by_user_id=0)
    return Success(msg="Deleted Successfully", data={"deleted_ids": menu_ids})


@router.get("/menus/pages/", summary="查看一级菜单")
async def _():
    menus = await Menu.filter(parent_id=0, constant=False)
    data = [{"key": menu.menu_name, "value": menu.id} for menu in menus]

    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuGetPages, by_user_id=0)
    return Success(data=data)


async def build_menu_button_tree(menus: list[Menu], parent_id: int = 0) -> list[dict]:
    """
    递归生成菜单按钮树
    :param menus:
    :param parent_id:
    :return:
    """
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            children = await build_menu_button_tree(menus, menu.id)
            menu_dict = {"id": f"parent${menu.id}", "label": menu.menu_name, "pId": menu.parent_id}
            if children:
                menu_dict["children"] = children
            else:
                menu_dict["children"] = [
                    {"id": button.id, "label": button.button_code, "pId": menu.id}
                    for button in await menu.by_menu_buttons
                ]
            tree.append(menu_dict)
    return tree


@router.get("/menus/buttons/tree/", summary="查看菜单按钮树")
async def _():
    menus_with_button = (
        await Menu.filter(constant=False).annotate(button_count=Count("by_menu_buttons")).filter(button_count__gt=0)
    )
    menu_objs = menus_with_button.copy()
    while len(menus_with_button) > 0:
        menu = menus_with_button.pop()
        if menu.parent_id != 0:
            menu = await Menu.get(id=menu.parent_id)
            menus_with_button.append(menu)
        else:
            menu_objs.append(menu)

    menu_objs = list(set(menu_objs))
    data = []
    if menu_objs:
        data = await build_menu_button_tree(menu_objs)

    await insert_log(log_type=LogType.AdminLog, log_detail_type=LogDetailType.MenuGetButtonsTree, by_user_id=0)
    return Success(data=data)
