sip -V -cgnd 15 -s -o -sub 2 -mlc metal3,metal4 -n 8 -i 0,8.001 -b 	metal4,metal3,metal2,metal1,li,poly,diff,FOX -j 0.8 -Maxw 12 -p 	metal5,key 0,8 - metal5.sip
sip -V -cgnd 15 -s -o -sub 2 -cp poly,allGates,diff -n 2.1 -i 	0,2.101 -b diff,FOX -t li,metal1,metal2,metal3,metal4,metal5 -j 0.15 	-Maxw 2.25 -p poly,key 0,2.1 - poly.sip
sip -V -cgnd 15 -s -o -sub 2 -mlc poly -n 1.4 -i 0,1.401 -b 	poly,diff,FOX -t metal1,metal2,metal3,metal4,metal5 -j 0.14 -Maxw 2.1 	-p li,key 0,1.4 - li.sip
sip -V -cgnd 15 -s -o -sub 2 -mlc poly,li -n 1.4 -i 0,1.401 -b 	li,poly,diff,FOX -t metal2,metal3,metal4,metal5 -j 0.14 -Maxw 2.1 -p 	metal1,key 0,1.4 - metal1.sip
sip -V -cgnd 15 -s -o -sub 2 -mlc li,metal1 -n 2.8 -i 0,2.801 -b 	metal1,li,poly,diff,FOX -t metal3,metal4,metal5 -j 0.14 -Maxw 2.1 -p 	metal2,key 0,2.8 - metal2.sip
sip -V -cgnd 15 -s -o -sub 2 -mlc metal1,metal2 -n 3 -i 0,3.001 -b 	metal2,metal1,li,poly,diff,FOX -t metal4,metal5 -j 0.3 -Maxw 4.5 -p 	metal3,key 0,3 - metal3.sip
sip -V -cgnd 15 -s -o -sub 2 -mlc metal2,metal3 -n 6 -i 0,6.001 -b 	metal3,metal2,metal1,li,poly,diff,FOX -t metal5 -j 0.3 -Maxw 4.5 -p 	metal4,key 0,6 - metal4.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -b 	metal3,metal2,metal1,li,poly,diff,FOX -Maxw 12 -p 	metal4:metal4_cut,key,metal5,key 0,8,0 - metal4_metal5.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -R metal5 -b 	metal2,metal1,li,poly,diff,FOX -k metal4:0.845 -Maxw 12 -p 	metal3:metal3_cut,key,metal5,key 0,8,0 - metal3_metal5.sip
sip -V -s -cgnd 15 -sub 2 -h -b metal2,metal1,li,poly,diff,FOX -t 	metal5 -Maxw 4.5 -p metal3:metal3_cut,key,metal4:metal4_cut,key 0,6,0 	- metal3_metal4.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -R metal4 -b 	metal1,li,poly,diff,FOX -t metal5 -k metal3:0.845 -Maxw 4.5 -p 	metal2:metal2_cut,key,metal4:metal4_cut,key 0,6,0 - metal2_metal4.sip
sip -V -s -cgnd 15 -sub 2 -h -b metal1,li,poly,diff,FOX -t 	metal4,metal5 -Maxw 4.5 -p 	metal2:metal2_cut,key,metal3:metal3_cut,key 0,3,0 - metal2_metal3.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -R metal3 -b li,poly,diff,FOX -t 	metal4,metal5 -k metal2:0.36 -Maxw 4.5 -p 	metal1:metal1_cut,key,metal3:metal3_cut,key 0,3,0 - metal1_metal3.sip
sip -V -s -cgnd 15 -sub 2 -h -b li,poly,diff,FOX -t 	metal3,metal4,metal5 -Maxw 2.1 -p 	metal1:metal1_cut,key,metal2:metal2_cut,key 0,2.8,0 - 	metal1_metal2.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -R metal2 -b poly,diff,FOX -t 	metal3,metal4,metal5 -k metal1:0.36 -Maxw 2.1 -p 	li:li_cut,key,metal2:metal2_cut,key 0,2.8,0 - li_metal2.sip
sip -V -s -cgnd 15 -sub 2 -h -b poly,diff,FOX -t 	metal2,metal3,metal4,metal5 -Maxw 2.1 -p 	li:li_cut,key,metal1:metal1_cut,key 0,1.4,0 - li_metal1.sip
sip -V -s -cgnd 15 -sub 2 -L3A -h -R metal1 -b diff,FOX -t 	metal2,metal3,metal4,metal5 -k li:0.1 -Maxw 2.25 -p 	poly:poly_cut,key,metal1:metal1_cut,key 0,2.1,0 - poly_metal1.sip
sip -V -s -cgnd 15 -sub 2 -h -R li,poly -b diff,FOX -t 	metal1,metal2,metal3,metal4,metal5 -Maxw 2.25 -p 	poly:poly_cut,key,li:li_cut,key 0,2.1,0 - poly_li.sip
sw3d -V -cgnd 15 -sub 2 -b metal3,metal2,metal1,li,poly,diff,FOX 	-p metal4:metal4_cut,metal5 - metal4_metal5.sw3d
sw3d -V -cgnd 15 -sub 2 -b metal2,metal1,li,poly,diff,FOX -t 	metal5 -p metal3:metal3_cut,metal4:metal4_cut - metal3_metal4.sw3d
sw3d -V -cgnd 15 -sub 2 -b metal1,li,poly,diff,FOX -t 	metal4,metal5 -p metal2:metal2_cut,metal3:metal3_cut - 	metal2_metal3.sw3d
sw3d -V -cgnd 15 -sub 2 -b li,poly,diff,FOX -t 	metal3,metal4,metal5 -p metal1:metal1_cut,metal2:metal2_cut - 	metal1_metal2.sw3d
sw3d -V -cgnd 15 -sub 2 -b poly,diff,FOX -t 	metal2,metal3,metal4,metal5 -p li:li_cut,metal1:metal1_cut - 	li_metal1.sw3d
sw3d -V -cgnd 15 -sub 2 -b diff,FOX -t 	metal1,metal2,metal3,metal4,metal5 -p poly:poly_cut,li:li_cut - 	poly_li.sw3d
