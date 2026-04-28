
Current status of different aspects of VIIRS-scag-drfs processing system

|Maturity Level      | Input data            | DEM         | NDGSI       | SLI         | Landmask    | infile msks | Code Lang(s)| Output format(s)  |
| :----------------  | :------:              |  :------:   | :------:    | :------:    | :------:    | :------:    |:------:     |             ----: |
| Barely works       |                       |             |             |             |             |             |             |                   |         | Copied from prev   |  MOD09GA              |**jpl_Comps**|**jpl_Comps**|**jpl_Comps**|**jpl_Comps**|**jpl_Comps**| **IDL, C**  | **tif, netCDF**   |
| In progress        |   *VJ1*               |             |             |             |             |             | *Python, C* |                   |
| Rough, but working |   *VNP*               |             |             |             |             |             |             |                   |
| Adequate, w prov   |                       |  *Karl*     |  *Karl*     | *Karl*      |  *Karl*     |    *Karl*   |             |                   |
| Best possible      |    VJ1                | _Karl+Prov_ | _Karl+Prov_ | _Karl+Prov_ | _Karl+Prov_ |_Karl+Prov_  |   _Python_  | _netCDF per guide_|

prov = "provenance" i.e. with useful documentation about source and creation of this information
