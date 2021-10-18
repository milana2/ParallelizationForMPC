add_executable(array_maximum array_maximum_main.cpp common/array_maximum.cpp)

if (NOT MOTION_BUILD_BOOST_FROM_SOURCES)
    find_package(Boost
            COMPONENTS
            program_options
            REQUIRED)
endif ()

target_link_libraries(array_maximum
        MOTION::motion
        Boost::program_options
        )
