// Retrieve the DICOM deidentification protocol from the server and set it in the global variable
function retrieveDicomDeidentificationProtocol() {
    //TODO fetch the protocol from the server
    // For now, we will use a hardcoded example
    const protocol = JSON.parse(`
{
    "dicomStandardVersion": "2025b",
    "default": "REJECT",
    "sopClass": {
        "1.2.840.10008.5.1.4.1.1.2": {
            "default": "X",
            "tag": {
                "(300A,078E)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,936C)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0032)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(3010,002D)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9383)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0066,002F)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A162)": null,
                "(0010,21A0)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1120)": null,
                "(0018,9346)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0034)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0026)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,5100)": null,
                "(0008,0013)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0620)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0400,0510)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1151)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0401)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9311)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0302)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0107)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1032)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0050)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,07A1)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0100)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,078F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0028)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0114)": null,
                "(0008,0015)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1020)": null,
                "(0010,0021)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0120)": null,
                "(0040,A033)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,2000)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,030A)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(7FE0,0001)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0100,0424)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,001B)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0031)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0253)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0062,000B)": null,
                "(0008,0308)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0121)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,937E)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0020,0010)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0561)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0020,1002)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,E021)": null,
                "(0010,0041)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0020,0020)": null,
                "(0008,0103)": null,
                "(0040,A168)": null,
                "(0040,1101)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,A120)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0602)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0072)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,103E)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,001C)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0600)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,060E)": null,
                "(0018,9375)": null,
                "(0018,1003)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1150)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,079F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,1301)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0050)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1160)": null,
                "(300A,065B)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,E031)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,936B)": null,
                "(0018,100A)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,2112)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9373)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,A122)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1201)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0513)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,1090)": null,
                "(0010,0020)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0022)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3002,012C)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9321)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,002A)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0121)": null,
                "(0032,1064)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1000)": null,
                "(0040,A123)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0021)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,1201)": null,
                "(0018,9378)": null,
                "(0018,115E)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0560)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1153)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0074,1212)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0221)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0055)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0124)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1030)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9364)": null,
                "(0028,0004)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9304)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0301)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9360)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,1024)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1130)": null,
                "(0008,1190)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9365)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,08EA)": null,
                "(0020,0062)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0563)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,1002)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,7FE0)": null,
                "(0018,9374)": null,
                "(0008,1052)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0105)": null,
                "(0008,0117)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A170)": null,
                "(0028,0102)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0050,0014)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,1030)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9073)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,E010)": null,
                "(0018,1048)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0020,0037)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9335)": null,
                "(0040,A034)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,0030)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0042)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,010C)": null,
                "(0008,1303)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0066,0036)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0022,1612)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(2050,0020)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0020,9172)": null,
                "(0008,0080)": null,
                "(0020,0060)": null,
                "(0018,0010)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0038,0062)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9380)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,010D)": null,
                "(0010,0016)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0200)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,001A)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,1202)": null,
                "(0028,2110)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(3010,002E)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,936D)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0562)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0033)": null,
                "(0040,0007)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,2294)": null,
                "(0010,0219)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0280)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0074,1057)": null,
                "(0020,0200)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1272)": null,
                "(0018,1002)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1008)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9330)": null,
                "(0008,0023)": null,
                "(0040,0518)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,1304)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0020,0032)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,1052)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0112)": null,
                "(0028,135A)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0012)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0015)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0012)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0306)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1111)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(3010,0043)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,0010)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9361)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,100A)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(300A,0795)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2162)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,9225)": null,
                "(0010,0024)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1301)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,0015)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,990D)": null,
                "(0400,0005)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0229)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0072,0052)": null,
                "(0008,0116)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0030)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0020,0012)": null,
                "(0028,1050)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9371)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0032,1033)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0066,0031)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0201)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0500)": null,
                "(0008,0060)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,051A)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,990C)": null,
                "(0008,0054)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(3002,012B)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2161)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(3010,0030)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,103F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0102)": null,
                "(0040,0039)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0791)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1044)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1160)": null,
                "(0028,3010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,0615)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1050)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9366)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,1103)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,2218)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0122)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0793)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9345)": null,
                "(0008,0017)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,936A)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(300A,0602)": null,
                "(0028,2002)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,0100)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,E022)": null,
                "(0018,1100)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,0050)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,0700)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0072,0056)": null,
                "(0040,0440)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0054,0412)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0071)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0072,0028)": null,
                "(0008,010F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,106C)": null,
                "(0010,1001)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9305)": null,
                "(7FE0,0002)": null,
                "(0018,9309)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0088,0140)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(60xx,0045)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0021)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1110)": null,
                "(0018,1204)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0031)": null,
                "(0028,3006)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,7050)": null,
                "(0010,0011)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,1056)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9328)": null,
                "(0008,0115)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0051)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,4000)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0254)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0054,0222)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0042)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1800)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A0B0)": null,
                "(0400,0551)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0054,0220)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300C,0002)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0250)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,1012)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0038,0010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0038,0014)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0022)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0009)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,3002)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,0108)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,114A)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0013)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(60xx,0011)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0015)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,001A)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,1051)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,1002)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,9220)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,100B)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,A163)": null,
                "(7FE0,0010)": null,
                "(0010,21B0)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0110)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0104)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0053)": null,
                "(0010,2110)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,1203)": null,
                "(2200,0005)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0565)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,1053)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,003A)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,1023)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1152)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,0060)": null,
                "(300C,0004)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1080)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1802)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1070)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,0043)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,0090)": null,
                "(0018,1049)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9004)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0100)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0081)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0020)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1115)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0032)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0035)": null,
                "(0400,0305)": null,
                "(60xx,3000)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,2180)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0106)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9353)": null,
                "(0008,010B)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0011)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0018)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0088,0200)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0304)": null,
                "(0010,0047)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,1055)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,A161)": null,
                "(0012,0083)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3002,010D)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0790)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9362)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,078C)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,1303)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0064)": null,
                "(0018,1043)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0038,0064)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,A124)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,106A)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9351)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0611)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1060)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,0006)": null,
                "(0018,0022)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9368)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,0040)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,07A0)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1205)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0050,0010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,0012)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9306)": null,
                "(0018,1040)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(FFFA,FFFA)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,0120)": null,
                "(0018,1140)": null,
                "(0020,0052)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0115)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,E024)": null,
                "(0008,1200)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3010,001D)": null,
                "(0018,1210)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9382)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0032)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0050,0018)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,0792)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0088,0130)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0020)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,0088)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(3002,010E)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0050,001B)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0021)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0400,0550)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,2228)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0046)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,936F)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0023)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,2203)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,E023)": null,
                "(0008,0081)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0032)": null,
                "(0040,0033)": null,
                "(0018,A003)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9352)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,009C)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,A002)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,1102)": null,
                "(0066,0030)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,2112)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,1302)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0024,0202)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0554)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0562)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,3010)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,1101)": null,
                "(0008,0090)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0060)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3002,012F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0212)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A032)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,1102)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,9215)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,2293)": null,
                "(0040,9224)": null,
                "(60xx,0010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0014)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9370)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0032,1034)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9318)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,010E)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0045)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0041)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,2299)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0028,0103)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0101)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0275)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1061)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0218)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0310)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0109)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0600)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0050,001C)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,937A)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0109)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0038,0500)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0082)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0100)": null,
                "(3002,012E)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(3010,001A)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,0050)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0054,0500)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0020,4000)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0051)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0002)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,9213)": null,
                "(0010,21D0)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0032,1060)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1271)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0050,001E)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0441)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2297)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,0515)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,001D)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9312)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0305)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9367)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(300A,078D)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0054,0410)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,E001)": null,
                "(0042,0013)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0213)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0036)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1047)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9372)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0008)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0070)": null,
                "(0040,0612)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0223)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1111)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0244)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0038,0060)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,002A)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0050,0013)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,E025)": null,
                "(0008,0300)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A043)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1302)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0215)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0032,1067)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,937C)": null,
                "(0018,9325)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0303)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0020,000E)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,1170)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0564)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,9216)": null,
                "(0018,1803)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0309)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(3010,001C)": null,
                "(0100,0410)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0794)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,0040)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0062)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1084)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1041)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0014)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,2220)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2292)": null,
                "(0028,1103)": null,
                "(0040,9212)": null,
                "(0040,A160)": null,
                "(0010,0022)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0020)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0052)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0245)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0073)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3002,0110)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0217)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1120)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,21C0)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0610)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300A,0675)": null,
                "(0008,1062)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0020,0013)": null,
                "(0018,9310)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(3002,010F)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,9520)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0551)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,0301)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1009)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,1022)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,9096)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,1104)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,1021)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0017)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,9211)": null,
                "(0072,0054)": null,
                "(0040,0520)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1046)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,A035)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9376)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0063)": null,
                "(0008,0008)": null,
                "(0040,0251)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0012,0054)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,2201)": null,
                "(0010,0216)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0084)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0123)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,1100)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,937D)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,1500)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0020)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,1030)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0028,0303)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0118)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,3003)": null,
                "(0040,1001)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,0214)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,E020)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,937F)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,0014)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1050)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(300A,0796)": null,
                "(0008,1110)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,0010)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0120)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0107)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,2295)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0027)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1010)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,030D)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0016)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1200)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,2230)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9938)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0005)": null,
                "(0008,1250)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9363)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0552)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0400,0110)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0032,1066)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(300C,0006)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,936E)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,1042)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1199)": null,
                "(0028,0034)": null,
                "(0008,009D)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(300A,012C)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0512)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1801)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0053)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,993A)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2296)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1155)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(4FFE,0001)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1041)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0010,1010)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0066,0032)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0105)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(60xx,0102)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0050,0019)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9332)": null,
                "(0018,A001)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0307)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0040)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,1048)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0082)": null,
                "(0040,A30A)": null,
                "(0008,010A)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1140)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,0260)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0106)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2210)": null,
                "(0008,030C)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0044)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0400,0015)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0096)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,030E)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0031)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0310)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,9214)": null,
                "(0040,A040)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,9210)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0520)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2202)": null,
                "(0028,0300)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,0012)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0040,E030)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,2298)": null,
                "(0040,059A)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,1190)": null,
                "(0020,1041)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0030)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0008,0030)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9307)": null,
                "(0018,9379)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0010,0222)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0050,0016)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0040,A390)": null,
                "(0018,937B)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9381)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,030F)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,2114)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,0302)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0012,0043)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0018,9323)": null,
                "(0010,1020)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0012,0085)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(3010,001B)": {
                    "default": "Z",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9377)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0100,0420)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0018,9369)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0020,0011)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0008,1040)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(300A,0613)": null,
                "(0008,1049)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,0119)": null,
                "(0010,2000)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                               },
                "(0008,030B)": null,
                "(0008,2111)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0010,0033)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(60xx,0022)": {
                    "default": "X",
                    "justification": "[AUTO] Module usage"
                },
                "(0020,1040)": {
                    "default": "Z",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0072,0026)": null,
                "(0040,A121)": {
                    "default": "D",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0020,000D)": {
                    "default": "U",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1072)": {
                    "default": "X",
                    "justification": "[AUTO] Basic Profile"
                },
                "(0008,1150)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0028,1054)": null,
                "(0018,9384)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0040,0035)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0100,0426)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0400,0010)": {
                    "default": "K",
                    "justification": "[AUTO] Attribute-Module type"
                },
                "(0018,9313)": {
                    "default": "X",
                    "justification": "[AUTO] Attribute-Module type"
                }
            }
        }
    }
}
`);
    return protocol;
}

globalThis.DEIDENTIFICATION_PROTOCOL = retrieveDicomDeidentificationProtocol();
