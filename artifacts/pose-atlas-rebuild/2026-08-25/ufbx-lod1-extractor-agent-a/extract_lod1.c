#include "ufbx.h"

#include <inttypes.h>
#include <locale.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MHR_LOD1_VERTICES ((size_t)18439)
#define MHR_LOD1_FACES ((size_t)36874)
#define MHR_LOD1_INDICES ((size_t)110622)

static int make_path(char *dst, size_t dst_size, const char *prefix, const char *suffix)
{
    int result = snprintf(dst, dst_size, "%s%s", prefix, suffix);
    return result >= 0 && (size_t)result < dst_size;
}

static const ufbx_mesh *find_lod1_mesh(const ufbx_scene *scene)
{
    const ufbx_mesh *match = NULL;
    size_t matches = 0;
    size_t i;

    for (i = 0; i < scene->meshes.count; ++i) {
        const ufbx_mesh *mesh = scene->meshes.data[i];
        if (mesh->num_vertices == MHR_LOD1_VERTICES) {
            match = mesh;
            ++matches;
        }
    }
    return matches == 1 ? match : NULL;
}

static int validate_mesh(const ufbx_mesh *mesh)
{
    size_t face_ix;

    if (mesh->num_vertices != MHR_LOD1_VERTICES ||
        mesh->num_faces != MHR_LOD1_FACES ||
        mesh->num_indices != MHR_LOD1_INDICES ||
        mesh->vertices.count != mesh->num_vertices ||
        mesh->vertex_indices.count != mesh->num_indices ||
        mesh->faces.count != mesh->num_faces) {
        fprintf(stderr, "Unexpected MHR LOD1 counts\n");
        return 0;
    }
    if (mesh->reversed_winding) {
        fprintf(stderr, "ufbx reports reversed_winding=true; refusing topology authority\n");
        return 0;
    }

    for (face_ix = 0; face_ix < mesh->faces.count; ++face_ix) {
        ufbx_face face = mesh->faces.data[face_ix];
        uint32_t a;
        uint32_t b;
        uint32_t c;

        if (face.num_indices != 3 || face.index_begin > mesh->vertex_indices.count - 3) {
            fprintf(stderr, "Face %zu is not a valid source triangle\n", face_ix);
            return 0;
        }
        a = mesh->vertex_indices.data[face.index_begin + 0];
        b = mesh->vertex_indices.data[face.index_begin + 1];
        c = mesh->vertex_indices.data[face.index_begin + 2];
        if (a >= mesh->num_vertices || b >= mesh->num_vertices || c >= mesh->num_vertices) {
            fprintf(stderr, "Face %zu has an out-of-range control-point index\n", face_ix);
            return 0;
        }
        if (a == b || b == c || c == a) {
            fprintf(stderr, "Face %zu is degenerate\n", face_ix);
            return 0;
        }
    }
    return 1;
}

static int write_vertices(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t i;
    if (!file) {
        fprintf(stderr, "Cannot open vertex output: %s\n", path);
        return 0;
    }
    for (i = 0; i < mesh->vertices.count; ++i) {
        ufbx_vec3 value = mesh->vertices.data[i];
        if (fprintf(file, "%zu\t%.17g\t%.17g\t%.17g\n",
                    i, (double)value.x, (double)value.y, (double)value.z) < 0) {
            fclose(file);
            fprintf(stderr, "Failed writing vertex output\n");
            return 0;
        }
    }
    if (fclose(file) != 0) {
        fprintf(stderr, "Failed closing vertex output\n");
        return 0;
    }
    return 1;
}

static int write_faces(const char *path, const ufbx_mesh *mesh)
{
    FILE *file = fopen(path, "wb");
    size_t face_ix;
    if (!file) {
        fprintf(stderr, "Cannot open face output: %s\n", path);
        return 0;
    }
    for (face_ix = 0; face_ix < mesh->faces.count; ++face_ix) {
        ufbx_face face = mesh->faces.data[face_ix];
        uint32_t a = mesh->vertex_indices.data[face.index_begin + 0];
        uint32_t b = mesh->vertex_indices.data[face.index_begin + 1];
        uint32_t c = mesh->vertex_indices.data[face.index_begin + 2];
        if (fprintf(file, "%zu\t%" PRIu32 "\t%" PRIu32 "\t%" PRIu32 "\n",
                    face_ix, a, b, c) < 0) {
            fclose(file);
            fprintf(stderr, "Failed writing face output\n");
            return 0;
        }
    }
    if (fclose(file) != 0) {
        fprintf(stderr, "Failed closing face output\n");
        return 0;
    }
    return 1;
}

int main(int argc, char **argv)
{
    ufbx_load_opts opts = { 0 };
    ufbx_error error;
    ufbx_scene *scene;
    const ufbx_mesh *mesh;
    char vertex_path[4096];
    char face_path[4096];

    if (argc != 3) {
        fprintf(stderr, "Usage: extract_lod1 INPUT_LOD1_FBX OUTPUT_PREFIX\n");
        return 2;
    }
    if (UFBX_HEADER_VERSION != ufbx_pack_version(0, 23, 0)) {
        fprintf(stderr, "Extractor requires ufbx header v0.23.0\n");
        return 3;
    }
    if (!make_path(vertex_path, sizeof(vertex_path), argv[2], ".vertices.tsv") ||
        !make_path(face_path, sizeof(face_path), argv[2], ".faces.tsv")) {
        fprintf(stderr, "Output prefix is too long\n");
        return 4;
    }
    setlocale(LC_NUMERIC, "C");

    scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) {
        fprintf(stderr, "Failed to load FBX: %.*s\n",
                (int)error.description.length, error.description.data);
        return 5;
    }
    if (ufbx_source_version != UFBX_HEADER_VERSION) {
        fprintf(stderr, "ufbx source/header version mismatch\n");
        ufbx_free_scene(scene);
        return 6;
    }

    mesh = find_lod1_mesh(scene);
    if (!mesh) {
        fprintf(stderr, "Expected exactly one 18439-control-point mesh\n");
        ufbx_free_scene(scene);
        return 7;
    }
    if (!validate_mesh(mesh)) {
        ufbx_free_scene(scene);
        return 8;
    }
    if (!write_vertices(vertex_path, mesh) || !write_faces(face_path, mesh)) {
        ufbx_free_scene(scene);
        return 9;
    }

    printf("{\"mesh_element_id\":%" PRIu32
           ",\"vertices\":%zu,\"faces\":%zu,\"indices\":%zu"
           ",\"reversed_winding\":false,\"ufbx_version\":\"0.23.0\""
           "}\n",
           mesh->element_id, mesh->num_vertices, mesh->num_faces,
           mesh->num_indices);
    ufbx_free_scene(scene);
    return 0;
}
