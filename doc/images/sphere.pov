#include "colors.inc"
#include "textures.inc"

background{ White }

camera {
  angle 45
  location <0, 0.5, -6>
  look_at <-0.6, 1, 0>

  up    1*y
  right (16/9)*x
}

/*light_source {
//  <-10, 30, -25> color White
  #local LDIST = 10;
  <0,LDIST,0> color Gray80
  fade_distance LDIST+2 // starts to fade outside this
  fade_power 4

  rotate <-45,0,35>
}*/

/*
light_source {
//  <10, 0.1, 15> color rgb<0,0.6,1>
  <20,0,0> color rgb<0,0.6,1>
  rotate <0,-50,1>
}*/


// White overhead circular light to cast soft shadow
light_source {
  <0,0,0> color White
  #local LRAD = 4;
  #local LDIST = 20;
  area_light LRAD*2*x, LRAD*2*z, 5, 5
    circular orient
    jitter
    adaptive 1

  fade_distance LDIST+2
  fade_power 1

  translate <-LRAD,LDIST,-LRAD>
  rotate <-35,0,25>
}


// Blue side light to add edge glow
light_source {
  <0,0,0> color rgb 2*<0,0.6,1>
  area_light 0.1*z, 4*y, 1, 10
    area_illumination on
    jitter
  translate <4,0,-0.5>
  rotate <0,-30,1>
}



/*fog {
  distance 130
  color Black
}*/

sky_sphere {
  pigment {
    gradient y
    color_map {
      [(1-cos(radians( 90)))/2 color Black]
      [(1-cos(radians(200)))/2 color rgb<0.04, 0.04, 0.04>]
    }
    scale 2
    translate -1
  }
}

sphere {
  <0, 0, 0>, 1
  texture {
    pigment {
      #local CSCALE = 0.13;
      checker pigment{Red}, pigment{White}, scale <CSCALE/2, CSCALE, CSCALE>
      warp { spherical orientation y }
    }
    finish {
      ambient 0.02
      specular 0.7 roughness 0.01
    }
  }

  rotate <-7,-4,-20>
  translate <0,1,0>
}


superellipsoid {
  <0.4, 0.4>

  texture {
    pigment { rgb<0,0,0.3> }
    finish {
      ambient 0.02
      specular 0.7 roughness 0.01
      reflection { 0.6 falloff 4 }
    }
  }

  translate <0,1,0>
  scale 0.8
  rotate <0,55,0>
  translate <-3.5, 0, 4>

}

plane {
  <0,1,0>, 0
  texture {
    pigment { rgb<0.06,0.07,0.09> }

    normal {
      average
      normal_map {
        [0.6 agate 0.1 agate_turb 1.9 scale 1.5 poly_wave 0.2]
        [0.4 agate 0.1 agate_turb 2.5 scale 0.2 poly_wave 0.1]
      }
      
    }

    finish {
      ambient 0
      reflection { 0.99
        falloff 2
//        metallic 0.1
      }
//      specular 0.7 roughness 0.01
      diffuse 0.2
      brilliance 1.5
    }

  }
}


/*
lathe {
  linear_spline
  6,
  <0,0>, <1,1>, <3,2>, <2,3>, <2,4>, <0,4>
  pigment { Blue }
  finish {
    ambient .3
    phong .75
  }
}*/
