#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from k3cloud_webapi_sdk.main import K3CloudApiSdk
from pyrda.dbms.rds import RdClient

def erp_save(app2,api_sdk,option,data,app3):

        erro_list = []
        sucess_num = 0
        erro_num = 0


        api_sdk.InitConfig(option['acct_id'], option['user_name'], option['app_id'],
                           option['app_sec'], option['server_url'])

        for i in data:

            try:

                if exist_order(api_sdk,i[0]['FDELIVERYNO'])!=True:

                        model={
                                "Model": {
                                    "FID": 0,
                                    "FBillNo": str(i[0]['FDELIVERYNO']),
                                    "FBillTypeID": {
                                        "FNUMBER": "QTCKD01_SYS"
                                    },
                                    "FStockOrgId": {
                                        "FNumber": "104"
                                    },
                                    "FPickOrgId": {
                                        "FNumber": "104"
                                    },
                                    "FStockDirect": "GENERAL",
                                    "FDate": str(i[0]['FDELIVERDATE']),
                                    "FCustId": {
                                        "FNumber": code_conversion(app2,"rds_vw_customer","FNAME",i[0]['FCUSTOMNAME'])
                                    },
                                    "FDeptId": {
                                        "FNumber": "BM000035"
                                    },
                                    "FStockerId": {
                                        "FNumber": "BSP00040"
                                    },
                                    "FStockerGroupId": {
                                        "FNumber": "SKCKZ01"
                                    },
                                    "FOwnerTypeIdHead": "BD_OwnerOrg",
                                    "FOwnerIdHead": {
                                        "FNumber": "104"
                                    },
                                    "FNote": str(i[0]['FTRADENO']),
                                    "FBaseCurrId": {
                                        "FNumber": "PRE001"
                                    },
                                    "F_SZSP_Assistant": {
                                        "FNumber": "LX04"
                                    },
                                    "FEntity": data_splicing(app2,i)
                                }
                            }

                        save_res=json.loads(api_sdk.Save("STK_MisDelivery",model))

                        if save_res['Result']['ResponseStatus']['IsSuccess']:

                            submit_result = ERP_submit(api_sdk, str(i[0]['FDELIVERYNO']))

                            if submit_result:

                                audit_result = ERP_Audit(api_sdk, str(i[0]['FDELIVERYNO']))

                                if audit_result:

                                    insertLog(app3, "其他出库单", str(i[0]['FDELIVERYNO']), "数据同步成功", "1")

                                    changeStatus(app3, str(i[0]['FDELIVERYNO']), "1")

                                    sucess_num=sucess_num+1

                                else:
                                    changeStatus(app3, str(i[0]['FDELIVERYNO']), "2")
                            else:
                                changeStatus(app3, str(i[0]['FDELIVERYNO']), "2")
                        else:

                            insertLog(app3, "其他出库单", str(i[0]['FDELIVERYNO']),save_res['Result']['ResponseStatus']['Errors'][0]['Message'],"2")

                            changeStatus(app3, str(i[0]['FDELIVERYNO']), "2")

                            erro_num=erro_num+1

                            erro_list.append(save_res)


                else:

                    insertLog(app3, "其他出库单", str(i[0]['FDELIVERYNO']),
                              "数据同步成功", "1")

                    changeStatus(app3, str(i[0]['FDELIVERYNO']), "1")

            except Exception as e:
                insertLog(app3, "其他出库单", str(i[0]['FDELIVERYNO']),"数据异常","2")

        dict = {
            "sucessNum": sucess_num,
            "erroNum": erro_num,
            "erroList": erro_list
        }
        return dict


def ERP_submit(api_sdk,FNumber):

    model={
        "CreateOrgId": 0,
        "Numbers": [FNumber],
        "Ids": "",
        "SelectedPostId": 0,
        "NetworkCtrl": "",
        "IgnoreInterationFlag": ""
    }

    res=json.loads(api_sdk.Submit("STK_MisDelivery",model))

    return res['Result']['ResponseStatus']['IsSuccess']

def ERP_Audit(api_sdk,FNumber):
    '''
    将订单审核
    :param api_sdk: API接口对象
    :param FNumber: 订单编码
    :return:
    '''

    model={
        "CreateOrgId": 0,
        "Numbers": [FNumber],
        "Ids": "",
        "InterationFlags": "STK_InvCheckResult",
        "NetworkCtrl": "",
        "IsVerifyProcInst": "",
        "IgnoreInterationFlag": ""
    }

    res = json.loads(api_sdk.Audit("STK_MisDelivery", model))

    return res['Result']['ResponseStatus']['IsSuccess']

def exist_order(api_sdk,FNumber):
    '''
    查看订单是否存在
    :param api_sdk:
    :param FNumber:
    :return:
    '''
    model = {
        "CreateOrgId": 0,
        "Number": FNumber,
        "Id": "",
        "IsSortBySeq": "false"
    }

    res = json.loads(api_sdk.View("STK_MisDelivery", model))

    return res['Result']['ResponseStatus']['IsSuccess']


def getClassfyData(app3,code):
    '''
    获得分类数据
    :param app2:
    :param code:
    :return:
    '''

    try:

        number=code['FDELIVERYNO']

        sql=f"select FInterID,FDELIVERYNO,FTRADENO,FBILLTYPE,FDELIVERYSTATUS,FDELIVERDATE,FSTOCK,FCUSTNUMBER,FCUSTOMNAME,FORDERTYPE,FPRDNUMBER,FPRDNAME,FPRICE,FNBASEUNITQTY,FLOT,FSUMSUPPLIERLOT,FPRODUCEDATE,FEFFECTIVEDATE,FMEASUREUNIT,DELIVERYAMOUNT,FTAXRATE,FSALER,FAUXSALER,Fisdo,FArStatus,FIsfree,UPDATETIME,FOUTID,FCurrencyName from RDS_ECS_ODS_sal_delivery where FDELIVERYNO='{number}'"

        res=app3.select(sql)

        return res

    except Exception as e:

        return []

def getCode(app3):
    '''
    查询出表中的编码
    :param app2:
    :return:
    '''

    sql="select distinct FDELIVERYNO from RDS_ECS_ODS_sal_delivery where FIsdo=0 and FIsFree=1"

    res=app3.select(sql)

    return res

def code_conversion(app2,tableName,param,param2):
    '''
    通过ECS物料编码来查询系统内的编码
    :param app2: 数据库操作对象
    :param tableName: 表名
    :param param:  参数1
    :param param2: 参数2
    :return:
    '''

    sql=f"select FNumber from {tableName} where {param}='{param2}'"

    res=app2.select(sql)

    if res==[]:

        return ""

    else:

        return res[0]['FNumber']

def code_conversion_org(app2,tableName,param,param2,param3,param4):
    '''
    通过ECS物料编码来查询系统内的编码
    :param app2: 数据库操作对象
    :param tableName: 表名
    :param param:  参数1
    :param param2: 参数2
    :return:
    '''

    sql=f"select {param4} from {tableName} where {param}='{param2}' and FOrgNumber='{param3}'"

    res=app2.select(sql)

    if res==[]:

        return ""

    else:

        return res[0][param4]


def changeStatus(app3,fnumber,status):
    '''
    将没有写入的数据状态改为2
    :param app2: 执行sql语句对象
    :param fnumber: 订单编码
    :param status: 数据状态
    :return:
    '''

    sql=f"update a set a.Fisdo={status} from RDS_ECS_ODS_sal_delivery a where FDELIVERYNO='{fnumber}'"

    app3.update(sql)


def insertLog(app2,FProgramName,FNumber,Message,FIsdo,cp='赛普'):
    '''
    异常数据日志
    :param app2:
    :param FNumber:
    :param Message:
    :return:
    '''

    sql="insert into RDS_ECS_Log(FProgramName,FNumber,FMessage,FOccurrenceTime,FCompanyName,FIsdo) values('"+FProgramName+"','"+FNumber+"','"+Message+"',getdate(),'"+cp+"','"+FIsdo+"')"

    app2.insert(sql)

def classification_process(app3,data):
    '''
    将编码进行去重，然后进行分类
    :param data:
    :return:
    '''

    res=fuz(app3,data)

    return res

def data_splicing(app2,data):
    '''
    将订单内的物料进行遍历组成一个列表，然后将结果返回给
    :param data:
    :return:
    '''

    list=[]

    for i in data:
        if json_model(app2,i):

            list.append(json_model(app2,i))

        else:
            return []

    return list

def fuz(app3,codeList):
    '''
    通过编码分类，将分类好的数据装入列表
    :param app2:
    :param codeList:
    :return:
    '''

    singleList=[]

    for i in codeList:

        data=getClassfyData(app3,i)
        singleList.append(data)

    return singleList



def json_model(app2, model_data):

    try:

        if model_data['FPRDNUMBER']=='1' or code_conversion_org(app2,"rds_vw_material","F_SZSP_SKUNUMBER",model_data['FPRDNUMBER'],"104","FNUMBER"):

            model = {
                "FMaterialId": {
                    "FNumber": "7.1.000001" if model_data['FPRDNUMBER']=='1' else code_conversion_org(app2,"rds_vw_material","F_SZSP_SKUNUMBER",model_data['FPRDNUMBER'],"104","FNUMBER"),
                },
                "FQty": str(model_data['FNBASEUNITQTY']),
                "FStockId": {
                    "FNumber": "SK01" if model_data['FSTOCK']=='苏州总仓' or model_data['FSTOCK']=='样品仓' else code_conversion(app2,"rds_vw_warehouse","FNAME",model_data['FSTOCK'])
                },
                "FLot": {
                    "FNumber": str(model_data['FLOT']) if isbatch(app2,model_data['FPRDNUMBER'])=='1' else ""
                },
                "FOwnerTypeId": "BD_OwnerOrg",
                "FOwnerId": {
                    "FNumber": "104"
                },
                "FStockStatusId": {
                    "FNumber": "KCZT01_SYS"
                },
                "FKeeperTypeId": "BD_KeeperOrg",
                "FDistribution": False,
                "FKeeperId": {
                    "FNumber": "104"
                },
                "FProduceDate": str(model_data['FPRODUCEDATE']) if iskfperiod(app2,model_data['FPRDNUMBER'])=='1' else "",
                "FExpiryDate" : str(model_data['FEFFECTIVEDATE']) if iskfperiod(app2,model_data['FPRDNUMBER'])=='1' else ""
            }

            return model

        else:
            return {}

    except Exception as e:

        return {}


def iskfperiod(app2,FNumber):
    '''
    查看物料是否启用保质期
    :param app2:
    :param FNumber:
    :return:
    '''

    sql=f"select FISKFPERIOD from rds_vw_fiskfperiod where F_SZSP_SKUNUMBER='{FNumber}'"

    res=app2.select(sql)

    if res==[]:

        return ""

    else:

        return res[0]['FISKFPERIOD']

def isbatch(app2,FNumber):

    sql=f"select FISBATCHMANAGE from rds_vw_fisbatch where F_SZSP_SKUNUMBER='{FNumber}'"

    res = app2.select(sql)

    if res == []:

        return ""

    else:

        return res[0]['FISBATCHMANAGE']

def otherOut(startDate,endDate,app2,app3,option):
    # app2 = RdClient(token='57DEDF26-5C00-4CA9-BBF7-57ECE07E179B')
    # app3 = RdClient(token='9B6F803F-9D37-41A2-BDA0-70A7179AF0F3')

    data = getCode(app3)

    if data:

        res = classification_process(app3, data)

        api_sdk = K3CloudApiSdk()

        msg=erp_save(app2, api_sdk, option, res, app3)

        return msg
    else:

        return {"message":"无订单需要同步"}


def otherOut_byOrder(app2,app3,option,data):
    '''
    按单据同步
    :param startDate:
    :param endDate:
    :return:
    '''

    api_sdk = K3CloudApiSdk()

    if data!=[] :

        res = classification_process(app3, data)

        if res!=[]:

            msg=erp_save(api_sdk=api_sdk, data=res, option=option, app2=app2, app3=app3)

            return msg

    else:

        return {"message":"SRC无此订单"}



