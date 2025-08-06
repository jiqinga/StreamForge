/**
 * Namespace Api
 *
 * All backend api type
 */
declare namespace Api {
  namespace Common {
    /** common params of paginating */
    interface PaginatingCommonParams {
      /** current page number */
      current: number;
      /** page size */
      size: number;
      /** total count */
      total: number;
    }

    /** common params of paginating query list data */
    interface PaginatingQueryRecord<T = any> extends PaginatingCommonParams {
      records: T[];
    }

    /** common search params of table */
    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'current' | 'size'>;

    /**
     * enable status
     *
     * - "1": enabled
     * - "2": disabled
     */
    type EnableStatus = '1' | '2';

    /** common record */
    type CommonRecord<T = any> = {
      /** record id */
      id: number;
      /** record creator */
      createBy: string;
      /** record create time */
      createTime: number;
      /** record updater */
      updateBy: string;
      /** record update time */
      updateTime: number;
      /** record status */
      statusType: EnableStatus | null;
      /** record fmt create time */
      fmtCreateTime: string;
      /** record fmt updateTime time */
      fmtUpdateTime: string;
    } & T;
  }

  /**
   * namespace Auth
   *
   * backend api module: "auth"
   */
  namespace Auth {
    interface LoginToken {
      token: string;
      refreshToken: string;
    }

    interface UserInfo {
      userId: string;
      userName: string;
      nickName: string;
      roles: string[];
      buttons: string[];
    }
  }

  /**
   * namespace Route
   *
   * backend api module: "route"
   */
  namespace Route {
    type ElegantConstRoute = import('@elegant-router/types').ElegantConstRoute;

    interface MenuRoute extends ElegantConstRoute {
      id: string;
    }

    interface UserRoute {
      routes: MenuRoute[];
      home: import('@elegant-router/types').LastLevelRouteKey;
    }
  }

  /**
   * namespace SystemManage
   *
   * backend api module: "systemManage"
   */
  namespace SystemManage {
    type CommonSearchParams = Pick<Common.PaginatingCommonParams, 'current' | 'size'>;

    /** common delete params */
    type CommonDeleteParams = { id: number | string };

    /** common batch delete params */
    type CommonBatchDeleteParams = { ids: string[] };

    type tableColumnSetting = { [tableId: string]: { [key: string]: boolean } };

    /** role */
    type Role = Common.CommonRecord<{
      /** role name */
      roleName: string;
      /** role code */
      roleCode: string;
      /** role description */
      roleDesc: string;
      /** role home */
      byRoleHomeId: number;
    }>;

    /** role add params */
    type RoleAddParams = Pick<
      Api.SystemManage.Role,
      'roleName' | 'roleCode' | 'roleDesc' | 'byRoleHomeId' | 'statusType'
    >;

    /** role update params */
    type RoleUpdateParams = CommonType.RecordNullable<Pick<Api.SystemManage.Role, 'id'>> & RoleAddParams;

    /** role search params */
    type RoleSearchParams = CommonType.RecordNullable<
      Pick<Api.SystemManage.Role, 'roleName' | 'roleCode' | 'statusType'> & CommonSearchParams
    >;

    /** role list */
    type RoleList = Common.PaginatingQueryRecord<Role>;

    /** role authorized */
    type RoleAuthorized = Api.SystemManage.Role & {
      byRoleMenuIds: number[];
      byRoleApiIds: number[];
      byRoleButtonIds: number[];
    };

    /** get role authorized params */
    type RoleAuthorizedParams = Pick<Api.SystemManage.RoleAuthorized, 'id'>;

    /** role authorized list */
    type RoleAuthorizedList = CommonType.RecordNullable<RoleAuthorized>;

    /** all role */
    type AllRole = Pick<Role, 'id' | 'roleName' | 'roleCode'>;

    /**
     * api method
     *
     * - "1": "GET"
     * - "2": "POST"
     * - "3": "PUT"
     * - "4": "PATCH"
     * - "5": "DELETE"
     */
    type methods = 'get' | 'post' | 'put' | 'patch' | 'delete';

    /** api */
    type Api = Common.CommonRecord<{
      /** api path */
      apiPath: string;
      /** api method */
      apiMethod: methods;
      /** api summary */
      summary: string;
      /** api tags name */
      tags: string[];
    }>;

    /** api add params */
    type ApiAddParams = Pick<Api.SystemManage.Api, 'apiPath' | 'apiMethod' | 'summary' | 'tags' | 'statusType'>;

    /** api update params */
    type ApiUpdateParams = CommonType.RecordNullable<Pick<Api.SystemManage.Api, 'id'>> & ApiAddParams;

    /** api search params */
    type ApiSearchParams = CommonType.RecordNullable<
      Pick<Api.SystemManage.Api, 'apiPath' | 'apiMethod' | 'summary' | 'tags' | 'statusType'> & CommonSearchParams
    >;

    /** api list */
    type ApiList = Common.PaginatingQueryRecord<Api>;

    /**
     * log type
     *
     * - "1": "ApiLog"
     * - "2": "UserLog"
     * - "3": "AdminLog"
     * - "4": "SystemLog"
     */
    type logTypes = '1' | '2' | '3' | '4';

    /**
     * api method
     *
     * - "1": "GET"
     * - "2": "POST"
     * - "3": "PUT"
     * - "4": "PATCH"
     * - "5": "DELETE"
     */
    type logDetailTypes =
      | '1101'
      | '1102'
      | '1201'
      | '1202'
      | '1203'
      | '1211'
      | '1212'
      | '1213'
      | '1301'
      | '1302'
      | '1303'
      | '1311'
      | '1312'
      | '1313'
      | '1314'
      | '1315'
      | '1401'
      | '1402'
      | '1403'
      | '1404'
      | '1411'
      | '1412'
      | '1413'
      | '1414'
      | '1415'
      | '1501'
      | '1502'
      | '1503'
      | '1504'
      | '1505'
      | '1506'
      | '1507'
      | '1511'
      | '1512'
      | '1513'
      | '1514'
      | '1515'
      | '1601'
      | '1611'
      | '1612'
      | '1613'
      | '1614'
      | '1615';

    /** log */
    type Log = Common.CommonRecord<{
      /** log type */
      logType: logTypes;
      /** log detail */
      logDetailType: logDetailTypes | null;
      /** create time */
      createTime: number;
      /** format create time */

      /** request domain */
      requestDomain: string;
      /** request path */
      requestPath: string;
      /** create time */
      responseCode: string;
      /** x-request-id */
      xRequestId: string;
      /** request params */
      requestParams: string;
      /** response data */
      responseData: string;
      /** user agent */
      userAgent: string;
      /** process time */
      processTime: string;
      /** ip address */
      ipAddress: string;

      /** by user id */
      byUser: string;
      /** user info */
      byUserInfo: User;
    }>;

    /** log add params */
    type LogAddParams = Pick<
      Api.SystemManage.Log,
      | 'logType'
      | 'logDetailType'
      | 'createTime'
      | 'byUser'
      | 'requestDomain'
      | 'requestPath'
      | 'responseCode'
      | 'xRequestId'
      | 'requestParams'
      | 'responseData'
      | 'userAgent'
      | 'processTime'
      | 'ipAddress'
    >;

    /** log update params */
    type LogUpdateParams = CommonType.RecordNullable<Pick<Api.SystemManage.Log, 'id'>> & Api.SystemManage.LogAddParams;

    /** log search params */
    type LogSearchParams = CommonType.RecordNullable<
      Pick<
        Api.SystemManage.Log,
        | 'logType'
        | 'logDetailType'
        | 'requestDomain'
        | 'requestPath'
        | 'createTime'
        | 'responseCode'
        | 'byUser'
        | 'xRequestId'
      > &
        CommonSearchParams & { timeRange: [number, number] }
    >;

    /** log list */
    type LogList = Common.PaginatingQueryRecord<Log>;

    /**
     * user gender
     *
     * - "1": "male"
     * - "2": "female"
     * - "3": "secret"
     */
    type UserGender = '1' | '2' | '3';

    /** user */
    type User = Common.CommonRecord<{
      /** user name */
      userName: string;
      /** password */
      password: string;
      /** user gender */
      userGender: UserGender | null;
      /** user nick name */
      nickName: string;
      /** user phone */
      userPhone: string;
      /** user email */
      userEmail: string;
      /** user role code collection */
      byUserRoleCodeList: string[];
    }>;

    /** user add params */
    type UserAddParams = Pick<
      Api.SystemManage.User,
      | 'userName'
      | 'password'
      | 'userGender'
      | 'nickName'
      | 'userPhone'
      | 'userEmail'
      | 'byUserRoleCodeList'
      | 'statusType'
    >;

    /** user update params */
    type UserUpdateParams = CommonType.RecordNullable<Pick<Api.SystemManage.User, 'id'> & UserAddParams>;

    /** user search params */
    type UserSearchParams = CommonType.RecordNullable<
      Pick<
        Api.SystemManage.User,
        | 'userName'
        | 'password'
        | 'userGender'
        | 'nickName'
        | 'userPhone'
        | 'userEmail'
        | 'statusType'
        | 'byUserRoleCodeList'
      > &
        CommonSearchParams
    >;

    /** user list */
    type UserList = Common.PaginatingQueryRecord<User>;

    /**
     * menu type
     *
     * - "1": directory
     * - "2": menu
     */
    type MenuType = '1' | '2';

    /** menu button */
    type MenuButton = {
      /**
       * button code
       *
       * it can be used to control the button permission
       */
      buttonCode: string;
      /** button description */
      buttonDesc: string;
    };

    /**
     * icon type
     *
     * - "1": iconify icon
     * - "2": local icon
     */
    type IconType = '1' | '2';

    /** props of elegant-router */
    type MenuPropsOfRoute = Pick<
      import('vue-router').RouteMeta,
      | 'i18nKey'
      | 'keepAlive'
      | 'constant'
      | 'order'
      | 'href'
      | 'hideInMenu'
      | 'activeMenu'
      | 'multiTab'
      | 'fixedIndexInTab'
      | 'query'
    >;

    /** menu */
    type Menu = Common.CommonRecord<{
      /** parent menu id */
      parentId: number;
      /** menu type */
      menuType: MenuType;
      /** menu name */
      menuName: string;
      /** route name */
      routeName: string;
      /** route path */
      routePath: string;
      /** component */
      component?: string;
      /** iconify icon name or local icon name */
      icon: string;
      /** icon type */
      iconType: IconType;
      /** buttons */
      buttons?: MenuButton[] | null;
      /** children menu */
      children?: Menu[] | null;
    }> &
      MenuPropsOfRoute;

    /** menu add params */
    type MenuAddParams = Pick<
      Api.SystemManage.Menu,
      | 'menuType'
      | 'menuName'
      | 'routeName'
      | 'routePath'
      | 'component'
      | 'order'
      | 'i18nKey'
      | 'icon'
      | 'iconType'
      | 'statusType'
      | 'parentId'
      | 'keepAlive'
      | 'constant'
      | 'href'
      | 'hideInMenu'
      | 'activeMenu'
      | 'multiTab'
      | 'fixedIndexInTab'
    > & {
      query: NonNullable<Api.SystemManage.Menu['query']>;
      buttons: NonNullable<Api.SystemManage.Menu['buttons']>;
      layout: string;
      page: string;
      pathParam: string;
    };

    /** menu update params */
    type MenuUpdateParams = CommonType.RecordNullable<Pick<Api.SystemManage.Menu, 'id'>> & MenuAddParams;

    /** menu list */
    type MenuList = Common.PaginatingQueryRecord<Menu>;

    /** menu tree */
    type MenuTree = {
      id: number;
      label: string;
      pId: number;
      children?: MenuTree[];
    };

    /** button tree */
    type ButtonTree = {
      id: number;
      label: string;
      pId: number;
      children?: ButtonTree[];
    };
  }
}

declare namespace StrmAPI {
  interface FileStats {
    total: number;
    video: number;
    audio: number;
    image: number;
    subtitle: number;
    metadata: number;
    other: number;
  }

  interface ParsedFile {
    path: string;
    file_type: string;
    size?: number;
    ctime?: string;
    mtime?: string;
    ext?: string;
    parent_dir?: string;
    name?: string;
  }

  interface UploadResult {
    filename: string;
    path: string;
    record_id: number;
  }

  interface DirectoryContent {
    directory_path: string;
    files: ParsedFile[];
    subdirectories: string[];
    stats: {
      file_count: number;
      subdirectory_count: number;
    };
  }

  interface ParseStats {
    total: number;
    video: number;
    audio: number;
    image: number;
    subtitle: number;
    metadata: number;
    other: number;
  }

  interface ParseResult {
    file_name: string;
    parsed_files: ParsedFile[];
    total_files: number;
    stats: ParseStats;
  }

  interface UploadRecord {
    id: number;
    filename: string;
    filesize: number;
    status: string;
    create_time: string;
    uploader_id: number;
    parse_time?: string;
  }

  interface FilterRuleResponse {
    id: number;
    create_time: string;
    update_time: string;
    name: string;
    file_type?: 'video' | 'audio' | 'image' | 'subtitle' | 'other';
    keyword?: string;
    path_pattern?: string;
    is_include: boolean;
  }

  interface MediaServer {
    id: number;
    name: string;
    server_type: string;
    base_url: string;
    is_default: boolean;
    description?: string;
    auth_required: boolean;
    create_time: string;
  }

  /**
   * Task type enum
   * - 'strm': STRM file generation task
   * - 'resource_download': Resource download task
   */
  type TaskType = 'strm' | 'resource_download';

  interface StrmTaskCreate {
    record_id: number;
    server_id: number;
    output_dir?: string;
    name?: string;
    task_type?: TaskType;
  }

  interface StrmFileDetail {
    id: number;
    source_path: string;
    target_path: string;
    file_type: string;
    file_size?: number;
    is_success: boolean;
    error_message?: string;
  }

  interface ResourceFileDetail {
    id: number;
    source_path: string;
    target_path: string;
    file_size?: number;
    is_success: boolean;
    download_progress?: number;
    error_message?: string;
  }

  interface StrmTaskDetail {
    id: number;
    name: string;
    status: string;
    task_type: TaskType;
    total_files: number;
    processed_files: number;
    success_files: number;
    failed_files: number;
    progress: number;
    start_time?: string;
    end_time?: string;
    output_dir: string;
    files: StrmFileDetail[] | ResourceFileDetail[];
    file_count: number;
    resource_files_count: number;
    error?: string;
    elapsed_time?: string;
    strm_files_count: number;
    strm_success: number;
    strm_failed: number;
    resource_success: number;
    resource_failed: number;
    video_files_count: number;
  }

  interface StrmTaskBrief {
    id: number;
    name: string;
    status: string;
    task_type: TaskType;
    total_files: number;
    processed_files: number;
    success_files: number;
    failed_files: number;
    progress: number;
    start_time?: string;
    end_time?: string;
  }

  interface StrmTaskResponse {
    total: number;
    page: number;
    page_size: number;
    tasks: StrmTaskBrief[];
  }

  interface StrmGenerateResult {
    task_id: number;
    name: string;
    status: string;
    result: {
      success: boolean;
      message: string;
      task_id: number;
      result?: any;
    };
  }

  interface ResourceDownloadTaskCreate {
    record_id: number;
    file_paths: string[];
    output_dir?: string;
    name?: string;
  }
}

declare namespace Api {
  namespace Page {
    interface PageParams {
      page?: number;
      page_size?: number;
    }

    interface PageResult<T> {
      total: number;
      page: number;
      page_size: number;
      records: T[];
    }
  }
}
