# include "spec.h"
int waterflag(int nbands, float *ldata, int wtrmaxrfl)
{
	int i, n, wf, water_flag;

	water_flag = 0;
	wf = 0;

	for (i=1;i<nbands;i++)
	{
		if (ldata[i] > wtrmaxrfl)
		{
			wf++;
		}
	}

	if (wf == 0)
	{
		water_flag = 1;
	}

	return water_flag;
}
