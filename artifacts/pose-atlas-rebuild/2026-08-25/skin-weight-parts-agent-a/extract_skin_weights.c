#include "ufbx.h"

#include <inttypes.h>
#include <stdio.h>

#define EXPECTED_VERTICES ((size_t)18439)
#define EXPECTED_FACES ((size_t)36874)
#define EXPECTED_CLUSTERS ((size_t)127)

static const ufbx_mesh *find_mesh(const ufbx_scene *scene)
{
    const ufbx_mesh *result = NULL;
    size_t matches = 0, i;
    for (i = 0; i < scene->meshes.count; ++i) {
        const ufbx_mesh *mesh = scene->meshes.data[i];
        if (mesh->num_vertices == EXPECTED_VERTICES && mesh->num_faces == EXPECTED_FACES) { result = mesh; ++matches; }
    }
    return matches == 1 ? result : NULL;
}

static void print_name(FILE *file, ufbx_string name)
{
    size_t i;
    for (i = 0; i < name.length; ++i) {
        char c = name.data[i];
        fputc(c == '\t' || c == '\r' || c == '\n' ? ' ' : c, file);
    }
}

int main(int argc, char **argv)
{
    ufbx_load_opts opts = {0};
    ufbx_error error;
    ufbx_scene *scene;
    const ufbx_mesh *mesh;
    const ufbx_skin_deformer *skin;
    FILE *clusters = NULL, *weights = NULL;
    size_t i, count = 0, unweighted = 0;
    if (argc != 4) { fputs("usage: extract_skin_weights INPUT_FBX CLUSTERS_TSV WEIGHTS_TSV\n", stderr); return 2; }
    if (UFBX_HEADER_VERSION != ufbx_pack_version(0, 23, 0)) return 3;
    scene = ufbx_load_file(argv[1], &opts, &error);
    if (!scene) { fprintf(stderr, "load failed: %.*s\n", (int)error.description.length, error.description.data); return 4; }
    mesh = find_mesh(scene);
    if (!mesh || mesh->skin_deformers.count != 1) { ufbx_free_scene(scene); return 5; }
    skin = mesh->skin_deformers.data[0];
    if (skin->clusters.count != EXPECTED_CLUSTERS || skin->vertices.count != EXPECTED_VERTICES) { ufbx_free_scene(scene); return 6; }
    if (fopen_s(&clusters, argv[2], "wb") != 0 || !clusters ||
        fopen_s(&weights, argv[3], "wb") != 0 || !weights) {
        if (clusters) fclose(clusters);
        if (weights) fclose(weights);
        ufbx_free_scene(scene);
        return 7;
    }
    fputs("cluster_index\tbone_element_id\tbone_name\tcluster_weight_count\n", clusters);
    for (i = 0; i < skin->clusters.count; ++i) {
        const ufbx_skin_cluster *cluster = skin->clusters.data[i];
        if (!cluster->bone_node) { fclose(clusters); fclose(weights); ufbx_free_scene(scene); return 8; }
        fprintf(clusters, "%zu\t%" PRIu32 "\t", i, cluster->bone_node->element_id);
        print_name(clusters, cluster->bone_node->name);
        fprintf(clusters, "\t%zu\n", cluster->num_weights);
    }
    fputs("vertex_index\trank\tcluster_index\tbone_name\tweight\n", weights);
    for (i = 0; i < skin->vertices.count; ++i) {
        ufbx_skin_vertex vertex = skin->vertices.data[i];
        size_t rank;
        if (vertex.num_weights == 0) ++unweighted;
        if ((size_t)vertex.weight_begin + vertex.num_weights > skin->weights.count) { fclose(clusters); fclose(weights); ufbx_free_scene(scene); return 9; }
        for (rank = 0; rank < vertex.num_weights; ++rank) {
            ufbx_skin_weight weight = skin->weights.data[vertex.weight_begin + rank];
            const ufbx_skin_cluster *cluster;
            if (weight.cluster_index >= skin->clusters.count) { fclose(clusters); fclose(weights); ufbx_free_scene(scene); return 10; }
            cluster = skin->clusters.data[weight.cluster_index];
            fprintf(weights, "%zu\t%zu\t%" PRIu32 "\t", i, rank, weight.cluster_index);
            print_name(weights, cluster->bone_node->name);
            fprintf(weights, "\t%.17g\n", (double)weight.weight);
            ++count;
        }
    }
    if (fclose(clusters) != 0 || fclose(weights) != 0) { ufbx_free_scene(scene); return 11; }
    printf("{\"status\":\"PASS\",\"vertices\":%zu,\"clusters\":%zu,\"weight_records\":%zu,\"unweighted_vertices\":%zu,\"max_weights_per_vertex\":%zu}\n",
        skin->vertices.count, skin->clusters.count, count, unweighted, skin->max_weights_per_vertex);
    ufbx_free_scene(scene);
    return 0;
}
